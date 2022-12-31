import logging
import redis
import requests
import api_store as api
from textwrap import dedent
from environs import Env
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Filters, Updater, CallbackContext
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler

from logger import BotLogsHandler
logger = logging.getLogger('telegram_logging')


def get_menu_markup():
    products = api.get_products()
    custom_keyboard = []
    for product in products['data']:
        custom_keyboard.append(
            [InlineKeyboardButton(product['attributes']['name'], callback_data=product['id'])]
        )
    custom_keyboard.append([InlineKeyboardButton('Корзина', callback_data='/cart')])
    return InlineKeyboardMarkup(
        inline_keyboard=custom_keyboard,
        resize_keyboard=True
    )


def start(update: Update, context: CallbackContext):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Please choose:',
        reply_markup=get_menu_markup()
    )
    return "HANDLE_MENU"


def send_info_product(update: Update, context: CallbackContext):
    if update.callback_query.data == '/cart':
        return get_cart_info(update, context)
    message_id = update.effective_message.message_id
    chat_id = update.effective_chat.id
    product_id = update.callback_query.data
    product_data = api.get_product(product_id)
    name = product_data['attributes']['name']
    price = product_data['meta']['display_price']['with_tax']['formatted']
    description = product_data['attributes'].get('description', 'Описание не задано')
    main_image_id = product_data['relationships']['main_image']['data']['id']
    link_image = api.get_file(file_id=main_image_id)['data']['link']['href']

    msg = f'''
        {name}
        {price}
        {description}
        '''
    custom_keyboard = [
        [
            InlineKeyboardButton('Положить в корзину', callback_data=product_id),
        ],
        [
            InlineKeyboardButton('Корзина', callback_data='/cart')
        ],
        [
            InlineKeyboardButton('Меню', callback_data='/start')
        ],

    ]
    context.bot.send_photo(
        chat_id,
        photo=link_image,
        caption=dedent(msg),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=custom_keyboard, resize_keyboard=True)
    )
    context.bot.delete_message(chat_id, message_id)

    return "HANDLE_DESCRIPTION"


def handle_description(update: Update, context: CallbackContext):
    callback_data = update.callback_query.data
    if callback_data == '/cart':
        return get_cart_info(update, context)
    quantity = 1
    product_id = callback_data
    api.get_cart(reference=update.effective_user.id)
    api.add_product_to_cart(
        product_id=product_id,
        quantity=quantity,
        reference=update.effective_user.id
    )
    return "HANDLE_DESCRIPTION"


def get_cart_info(update: Update, context: CallbackContext):
    total_value = (
        api.get_cart(update.effective_user.id)
        ['data']['meta']['display_price']['without_tax']['formatted']
    )
    cart_items = api.get_cart_items(update.effective_user.id)
    msg = ''
    custom_keyboard = []
    for item in cart_items['data']:
        msg += f'''
        {item['name']}
        {item['description']}
        {item['meta']['display_price']['without_tax']['unit']['formatted']}
        {item['quantity']}шт. за {item['meta']['display_price']['without_tax']['value']['formatted']}
        '''
        custom_keyboard.append(
            [InlineKeyboardButton(f'Убрать из корзины {item["name"]}', callback_data=item['id'])]
        )
    custom_keyboard.append([InlineKeyboardButton('Меню', callback_data='/start')])
    custom_keyboard.append([InlineKeyboardButton('Оплата', callback_data='/pay')])
    msg = f'''
        {msg}        
        Total: {total_value}
        '''
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=dedent(msg),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=custom_keyboard, resize_keyboard=True)
    )

    return 'HANDLER_CART'


def handler_cart(update: Update, context: CallbackContext):
    if update.callback_query.data == '/pay':
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Введите ваш email',
        )
        return 'WAITING_EMAIL'
    id_cart_item = update.callback_query.data
    api.remove_cart_item(update.effective_user.id, id_cart_item)
    total_value = (
        api.get_cart(update.effective_user.id)
        ['data']['meta']['display_price']['without_tax']['formatted']
    )
    cart_items = api.get_cart_items(update.effective_user.id)
    msg = ''
    custom_keyboard = []
    for item in cart_items['data']:
        msg += f'''
            {item['name']}
            {item['description']}
            {item['meta']['display_price']['without_tax']['unit']['formatted']}
            {item['quantity']}шт. за {item['meta']['display_price']['without_tax']['value']['formatted']}
            '''
        custom_keyboard.append(
            [InlineKeyboardButton(f'Убрать из корзины {item["name"]}', callback_data=item['id'])]
        )
    custom_keyboard.append([InlineKeyboardButton('Меню', callback_data='/start')])
    msg = f'''
            {msg}        
            Total: {total_value}
            '''
    context.bot.edit_message_text(
        chat_id=update.effective_chat.id,
        message_id=update.effective_message.message_id,
        text=dedent(msg),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=custom_keyboard, resize_keyboard=True)
    )
    return 'HANDLER_CART'


def waiting_email(update: Update, context: CallbackContext):
    email_user = update.message.text
    try:
        api.create_customer(update.effective_user.username, email_user)
    except requests.exceptions.HTTPError:
        print('Клиент уже существует')
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Спасибо. Мы свяжемся с Вами!\nPlease choose:',
        reply_markup=get_menu_markup()
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
        'HANDLE_MENU': send_info_product,
        'HANDLE_DESCRIPTION': handle_description,
        'CART_INFO': get_cart_info,
        'HANDLER_CART':  handler_cart,
        'WAITING_EMAIL': waiting_email
    }
    state_handler = states_functions[user_state]
    api.check_token()
    try:
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
    updater.logger.warning('Бот Telegram "fish-shop" запущен')
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))
    updater.start_polling()
