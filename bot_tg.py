import logging
import redis
import requests
import api_store as api
from textwrap import dedent
from environs import Env
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Filters, Updater, CallbackContext
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler
from telegram.constants import PARSEMODE_HTML

from logger import BotLogsHandler
logger = logging.getLogger('telegram_logging')

MENU_TEXT = 'Пожалуйста выберите:'
THANK_TEXT = 'Спасибо. Мы свяжемся с Вами!'
NONE_CART_TEXT = 'Нет в корзине'


def get_main_menu(start_product=0, offset_products=10, number_line_buttons=2):
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


def create_cart_msg(update: Update):
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
    msg = f'''
            {msg}        
            <b>Общая стоимость: {total_value}</b>
            '''
    return msg, custom_keyboard


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
            text='Введите ваш email',
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
    email_user = update.message.text
    try:
        api.create_customer(update.effective_user.username, email_user)
    except requests.exceptions.HTTPError:
        print('Клиент уже существует')
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f'{THANK_TEXT}\n{MENU_TEXT}',
        reply_markup=get_main_menu()
    )
    return 'HANDLE_MENU'


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
        'HANDLE_WAITING': handle_waiting
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
    updater = Updater(token)
    updater.logger.addHandler(BotLogsHandler(
        token=env('TELEGRAM_TOKEN_LOG'),
        chat_id=env('CHAT_ID_LOG')
    ))
    dispatcher = updater.dispatcher
    dispatcher.redis = redis.Redis(host=database_host, port=database_port, password=database_password)
    updater.logger.warning('Бот Telegram "pizza-payments" запущен')
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))
    updater.start_polling()
