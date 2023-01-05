import logging
import os
import re
from pprint import pprint

import redis
import requests
import api_store as api
from textwrap import dedent
from environs import Env
from geo_informer import fetch_coordinates, get_min_distance_branch
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Filters, Updater, CallbackContext, ContextTypes
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler
from telegram.constants import PARSEMODE_HTML

from logger import BotLogsHandler
logger = logging.getLogger('telegram_logging')

MENU_TEXT = 'Пожалуйста выберите:'
THANK_TEXT = 'Спасибо. Мы свяжемся с Вами!'
NONE_CART_TEXT = 'Нет в корзине'
GEO_REQUEST_TEXT = '<b>Для доставки вашего заказа пришлите нам ваш адрес текстом или геолокацию</b>'
AFTER_EMAIL_TEXT = '<i>Либо продолжите выбор:</i>'
AFTER_GEO_TEXT = '<i>Вы можете продолжить выбор, либо уточните адрес:</i>'
REPIET_SEND_COORD = '<b>Извините, но мы не смогли определить ваши координаты!</b>'
MESSAGE_AFTER_ORDER = f'''
                       Приятного аппетита!
                       Если Вы все еще не получили свою пиццу, то она будет для вас бесплатно! 
                       '''
MESSAGE_AFTER_PICKUP_ORDER = 'Ваш заказ уже готов и ждет вас!'


def get_main_menu(start_product=0, offset_products=10, number_line_buttons=2, restart=False):
    if restart:
        custom_keyboard = [[InlineKeyboardButton('Вернуться в меню', callback_data='/start')]]
        return InlineKeyboardMarkup(
            inline_keyboard=custom_keyboard,
            resize_keyboard=True
        )
    products = api.get_products()['data']
    end_index = min(start_product + offset_products, len(products))
    displayed_products = products[start_product: end_index]
    custom_keyboard = []
    button_line = []
    for number, product in enumerate(displayed_products, start=1):
        button_line.append(InlineKeyboardButton(product['attributes']['name'], callback_data=product['id']))
        if len(button_line) == number_line_buttons or len(button_line) == 1 and number == len(displayed_products):
            custom_keyboard.append(button_line)
            button_line = []
    next_product = end_index if len(products) > end_index else 0
    previous_index = start_product - offset_products
    previous_product = previous_index if previous_index >= 0 else len(products) - offset_products
    custom_keyboard.append([
        InlineKeyboardButton('<<<   Назад', callback_data=previous_product),
        InlineKeyboardButton('Вперед   >>>', callback_data=next_product)
    ])
    custom_keyboard.append([InlineKeyboardButton('Корзина', callback_data='/cart')])
    return InlineKeyboardMarkup(
        inline_keyboard=custom_keyboard,
        resize_keyboard=True
    )


def get_product_info_menu(product_id, price):
    custom_keyboard = [
        [InlineKeyboardButton('Добавить в корзину', callback_data=f'{product_id}:{price}')],
        [
            InlineKeyboardButton('Корзина', callback_data='/cart'),
            InlineKeyboardButton('Меню', callback_data='/start')
        ]
    ]
    return InlineKeyboardMarkup(
        inline_keyboard=custom_keyboard,
        resize_keyboard=True
    )


def start(update: Update, context: CallbackContext):
    login_user = update.effective_user.username
    os.environ[f'{login_user}_STEP_HANDLE'] = '1'
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=MENU_TEXT,
        reply_markup=get_main_menu()
    )

    return "HANDLE_MENU"


def send_product_info(update: Update, context: CallbackContext):
    if update.callback_query.data == '/cart':
        return get_cart_info(update, context)
    if update.callback_query.data.isdigit():
        start_product = int(update.callback_query.data)
        context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=update.effective_message.message_id,
            text=MENU_TEXT,
            reply_markup=get_main_menu(start_product)
        )
        return "HANDLE_MENU"
    message_id = update.effective_message.message_id
    chat_id = update.effective_chat.id
    product_id = update.callback_query.data
    product_data = api.get_product(product_id)
    name = product_data['data']['attributes']['name']
    price = product_data['data']['meta']['display_price']['with_tax']['formatted']
    description = product_data['data']['attributes'].get('description', 'Описание не задано')
    main_image_id = product_data['data']['relationships']['main_image']['data']['id']
    link_image = api.get_file(file_id=main_image_id)['data']['link']['href']
    cart_items = api.get_cart_items(update.effective_user.id)
    quantity = [item['quantity'] for item in cart_items['data'] if item['product_id'] == product_id]
    quantity_msg = f'<b>В корзине: {quantity[0]} шт.</b>' if quantity else NONE_CART_TEXT
    msg = f'''
        <b>{name}</b>
        <i>{price}</i>
        {description}
        '''
    context.bot.send_photo(
        chat_id,
        photo=link_image,
        caption=dedent(msg),
        parse_mode=PARSEMODE_HTML
    )
    context.bot.send_message(
        chat_id,
        text=quantity_msg,
        reply_markup=get_product_info_menu(product_id, price),
        parse_mode=PARSEMODE_HTML
    )
    context.bot.delete_message(chat_id, message_id)

    return "HANDLE_DESCRIPTION"


def handle_description(update: Update, context: CallbackContext):
    callback_data = update.callback_query.data
    if callback_data == '/cart':
        return get_cart_info(update, context)
    previous_msg = update.effective_message.text
    product_info = callback_data.split(':')
    product_id = product_info[0]
    price = product_info[1]
    api.add_product_to_cart(
        product_id=product_id,
        quantity=1,
        reference=update.effective_user.id
    )
    if previous_msg == NONE_CART_TEXT:
        msg = '<b>В корзине: 1 шт.</b>'
    else:
        quantity = int(previous_msg.split()[2])
        msg = f'<b>В корзине: {quantity + 1} шт.</b>'
    answer_callback_query_text = f'''
        Добавлено в корзину
        по цене {price} за 1 шт.
        '''
    context.bot.edit_message_text(
        chat_id=update.effective_chat.id,
        message_id=update.effective_message.message_id,
        text=msg,
        reply_markup=get_product_info_menu(product_id, price),
        parse_mode=PARSEMODE_HTML
    )
    context.bot.answer_callback_query(
        update.callback_query.id,
        text=dedent(answer_callback_query_text),
        show_alert=True
    )

    return "HANDLE_DESCRIPTION"


def create_cart_msg(update: Update, delivery_address=None):
    login_user = update.effective_user.username
    total_value = (
        api.get_cart(update.effective_user.id)
        ['data']['meta']['display_price']['without_tax']['formatted']
    )
    cart_items = api.get_cart_items(update.effective_user.id)
    msg = ''
    custom_keyboard = []
    for item in cart_items['data']:
        msg += f'''
                <b>{item['name']}</b>
                {item['description']}
                {item['meta']['display_price']['without_tax']['unit']['formatted']}
                <i>{item['quantity']} шт. за {item['meta']['display_price']['without_tax']['value']['formatted']}</i>
                '''
        custom_keyboard.append(
            [InlineKeyboardButton(f'Убрать из корзины: {item["name"]}', callback_data=item['id'])]
        )
    custom_keyboard.append([InlineKeyboardButton('Меню', callback_data='/start')])
    custom_keyboard.append([InlineKeyboardButton('Оплата', callback_data='/pay')])
    if not delivery_address:
        summary_msg = f'''
                {msg}        
                <b>Общая стоимость: {total_value}</b>
                '''
    else:
        summary_msg = f'''
                {msg}        
                <b>Общая стоимость: {total_value}</b>
                   
                <b>Адрес доставки: {delivery_address}</b>
                <b>Телефон заказчика: {os.environ[f'{login_user}_PHONE']}</b>
                '''
    return summary_msg, custom_keyboard


def get_cart_info(update: Update, context: CallbackContext):
    msg, custom_keyboard = create_cart_msg(update)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=dedent(msg),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=custom_keyboard, resize_keyboard=True),
        parse_mode=PARSEMODE_HTML
    )

    return 'HANDLER_CART'


def handler_cart(update: Update, context: CallbackContext):
    if update.callback_query.data == '/pay':
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Введите ваш email, либо продолжите выбор:',
            reply_markup=get_main_menu(restart=True)
        )
        return 'HANDLE_WAITING'
    id_cart_item = update.callback_query.data
    api.remove_cart_item(update.effective_user.id, id_cart_item)
    msg, custom_keyboard = create_cart_msg(update)
    context.bot.edit_message_text(
        chat_id=update.effective_chat.id,
        message_id=update.effective_message.message_id,
        text=dedent(msg),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=custom_keyboard, resize_keyboard=True),
        parse_mode=PARSEMODE_HTML
    )
    return 'HANDLER_CART'


def handle_waiting(update: Update, context: CallbackContext):
    login_user = update.effective_user.username
    if os.environ.get(f'{login_user}_STEP_HANDLE', '1') == '1':
        actual_return = 'HANDLE_WAITING'
        user_email = update.message.text.lower().strip()
        email_rule = re.compile(r'(^\S+@\S+\.\S+$)', flags=re.IGNORECASE)
        if email_rule.search(user_email):
            os.environ[f'{login_user}_EMAIL'] = user_email
            msg = 'Введите Ваш телефон'
            try:
                os.environ[f'{login_user}_STEP_HANDLE'] = '2'
                customer = api.create_customer(login_user, user_email)
                os.environ[f'{login_user}_CURRENT_CUSTOMER_ID'] = customer['data']['id']
            except requests.exceptions.HTTPError:
                found_user = api.get_all_customers(user_email)
                os.environ[f'{login_user}_CURRENT_CUSTOMER_ID'] = found_user['data'][0].get('id')
        else:
            msg = f'Введите корректный email'
            os.environ[f'{login_user}_STEP_HANDLE'] = '1'
    elif os.environ[f'{login_user}_STEP_HANDLE'] == '2':
        user_phone = update.message.text
        phone_rule = re.compile(r'(^[+0-9]{1,3})*([0-9]{10,11}$)')
        if phone_rule.search(user_phone):
            actual_return = 'HANDLE_LOCATION'
            os.environ[f'{login_user}_STEP_HANDLE'] = '1'
            os.environ[f'{login_user}_PHONE'] = user_phone
            msg = f'{THANK_TEXT}\n{GEO_REQUEST_TEXT}\n{AFTER_EMAIL_TEXT}'
        else:
            actual_return = 'HANDLE_WAITING'
            msg = f'Введите корректный номер телефона'

    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=msg,
        reply_markup=get_main_menu(restart=True),
        parse_mode=PARSEMODE_HTML
    )
    return actual_return


def get_button_delivery(delivery: bool = True, pickup: bool = True):
    if delivery and pickup:
        custom_keyboard = [
            [InlineKeyboardButton('Доставка', callback_data='delivery')],
            [InlineKeyboardButton('Самовывоз', callback_data='pickup')],
            [InlineKeyboardButton('Вернуться в меню', callback_data='/start')]
        ]
    elif not delivery and pickup:
        custom_keyboard = [
            [InlineKeyboardButton('Самовывоз', callback_data='pickup')],
            [InlineKeyboardButton('Вернуться в меню', callback_data='/start')]
        ]
    else:
        custom_keyboard = [
            [InlineKeyboardButton('Вернуться в меню', callback_data='/start')]
        ]

    return InlineKeyboardMarkup(
        inline_keyboard=custom_keyboard,
        resize_keyboard=True
    )


def handle_location(update: Update, context: CallbackContext):
    login_user = update.effective_user.username
    message = None
    address = None
    if update.edited_message:
        message = update.edited_message
    else:
        message = update.message
    if message and message.location:
        current_pos = (message.location.latitude, message.location.longitude)
    else:
        address = update.effective_message.text
        current_pos = fetch_coordinates(os.environ['YANDEX_GEO_TOKEN'], address)

    if current_pos:
        branch_address, branch_dist, telegram_id = get_min_distance_branch(current_pos)
        user_email = os.environ[f'{login_user}_EMAIL']
        user_phone = os.environ[f'{login_user}_PHONE']
        existing_entry = api.get_entry_by_pos(user_email, user_phone, current_pos)
        address = address if address else 'Пользователь не указал адрес'
        if not existing_entry:
            customer_address_entry = api.create_entry(
                flow_slug='customer-address',
                fields_data={
                    'address': address,
                    'email': user_email.lower().strip(),
                    'phone': user_phone,
                    'latitude': current_pos[0],
                    'longitude': current_pos[1]
                }
            )
            api.create_entry_relationship(
                flow_slug='customer-address',
                entry_id=customer_address_entry['data']['id'],
                field_slug='customer',
                resource_type='customer',
                resource_id=os.environ[f'{login_user}_CURRENT_CUSTOMER_ID']
            )
        reply_markup = get_button_delivery()
        if branch_dist <= 0.5:
            msg = f'''
                   Можете забрать пиццу из нашей пиццерии неподалеку?
                   Она всего в {round(branch_dist*1000, 0)} метров от Вас!
                   Вот её адрес: {branch_address}.
                   А можем и бесплатно доставить нам не сложно.
                   '''
        elif branch_dist <= 5:
            msg = f'''
                   Похоже придется ехать до Вас на самокате.
                   Доставка будет стоить 100 р.
                   Доставляем или самовывоз?
                   '''
        elif branch_dist <= 20:
            msg = f'''
                   Похоже придется ехать до Вас на автомобиле.
                   Доставка будет стоить 300 р.
                   Доставляем или самовывоз?
                   '''
        elif branch_dist <= 50:
            reply_markup = get_button_delivery(delivery=False)
            msg = f'''
                   Простите но так далеко мы пиццу не доставляем.
                   Ближайшая пиццерия от Вас в {round(branch_dist, 0)} км.
                   Но вы может забрать её самостоятельно.
                   Оформляем самовывоз?
                   '''
        else:
            reply_markup = get_button_delivery(pickup=False)
            msg = f'''
                   Простите но так далеко мы пиццу не доставляем.
                   Ближайшая пиццерия от Вас в {round(branch_dist, 0)} км.
                   Мы уверены, что есть другие пиццерии гораздо ближе.
                   Либо уточните адрес доставки.
                   '''
        msg = f'{dedent(msg)}\n{AFTER_GEO_TEXT}'
    else:
        reply_markup = get_main_menu(restart=True)
        msg = f'{THANK_TEXT}\n{REPIET_SEND_COORD}\n{AFTER_GEO_TEXT}'

    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=msg,
        reply_markup=reply_markup,
        parse_mode=PARSEMODE_HTML
    )
    if current_pos and branch_dist <= 50:
        os.environ[f'{login_user}_DELIVERY_ADDRESS'] = address
        os.environ[f'{login_user}_DELIVERY_LATITUDE'] = str(current_pos[0])
        os.environ[f'{login_user}_DELIVERY_LONGITUDE'] = str(current_pos[1])
        os.environ[f'{login_user}_DELIVERY_TELEGRAM_ID'] = telegram_id
        os.environ[f'{login_user}_BRANCH_ADDRESS'] = branch_address

        return 'HANDLE_DELIVERY'
    return 'HANDLE_LOCATION'


def handle_delivery(update: Update, context: CallbackContext):
    callback_data = update.callback_query.data
    login_user = update.effective_user.username
    if callback_data == 'delivery':
        msg = f'''
               Спасибо, что выбрали нашу пиццу.
               Ваш заказ уже готовиться и скоро будет доставлен.
               '''
        delivery_address = os.environ[f'{login_user}_DELIVERY_ADDRESS']
        delivery_latitude = os.environ[f'{login_user}_DELIVERY_LATITUDE']
        delivery_longitude = os.environ[f'{login_user}_DELIVERY_LONGITUDE']
        delivery_telegram_id = os.environ[f'{login_user}_DELIVERY_TELEGRAM_ID']
        cart_msg, __ = create_cart_msg(update, delivery_address=delivery_address)

        context.bot.send_message(
            chat_id=delivery_telegram_id,
            text=dedent(cart_msg),
            parse_mode=PARSEMODE_HTML
        )
        context.bot.send_location(
            chat_id=delivery_telegram_id,
            latitude=float(delivery_latitude),
            longitude=float(delivery_longitude)
        )
        context.job_queue.run_once(callback_after_order, 10, context=update.effective_chat.id)
    elif callback_data == 'pickup':
        msg = f'''
               Спасибо, что выбрали нашу пиццу.
               Вы можете забрать свой заказ по адресу:
               {os.environ[f'{login_user}_BRANCH_ADDRESS']}
               '''
        context.job_queue.run_once(callback_after_pickup_order, 1200, context=update.effective_chat.id)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=dedent(msg),
        reply_markup=get_main_menu(restart=True),
        parse_mode=PARSEMODE_HTML
    )
    return 'HANDLE_LOCATION'


def callback_after_order(context: CallbackContext):
    context.bot.send_message(
        chat_id=context.job.context,
        text=dedent(MESSAGE_AFTER_ORDER)
    )


def callback_after_pickup_order(context: CallbackContext):
    context.bot.send_message(
        chat_id=context.job.context,
        text=dedent(MESSAGE_AFTER_PICKUP_ORDER)
    )


def handle_users_reply(update: Update, context: CallbackContext):
    db = context.dispatcher.redis
    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return
    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = db.get(chat_id).decode("utf-8")
    states_functions = {
        'START': start,
        'HANDLE_MENU': send_product_info,
        'HANDLE_DESCRIPTION': handle_description,
        'CART_INFO': get_cart_info,
        'HANDLER_CART':  handler_cart,
        'HANDLE_WAITING': handle_waiting,
        'HANDLE_LOCATION': handle_location,
        'HANDLE_DELIVERY': handle_delivery,
    }
    state_handler = states_functions[user_state]
    try:
        api.check_token()
        next_state = state_handler(update, context)
    except Exception as err:
        api.check_token(error=True)
        next_state = state_handler(update, context)
        print(err)
    db.set(chat_id, next_state)


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    env = Env()
    env.read_env()
    api.check_token()

    token = env('TELEGRAM_TOKEN')
    database_password = env('DATABASE_PASSWORD')
    database_host = env('DATABASE_HOST')
    database_port = env('DATABASE_PORT')
    updater = Updater(token, use_context=True)
    updater.logger.addHandler(BotLogsHandler(
        token=env('TELEGRAM_TOKEN_LOG'),
        chat_id=env('CHAT_ID_LOG')
    ))
    dispatcher = updater.dispatcher
    dispatcher.redis = redis.Redis(host=database_host, port=database_port, password=database_password)
    updater.logger.warning('Бот Telegram "pizza-payments" запущен')
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply, pass_job_queue=True))
    dispatcher.add_handler(MessageHandler(Filters.location, handle_location))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))
    updater.start_polling()
    updater.idle()
