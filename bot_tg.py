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
