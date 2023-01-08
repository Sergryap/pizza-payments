from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

import api_store as api


def get_restart_button(skip=False):
    custom_keyboard = [[InlineKeyboardButton('Вернуться в меню', callback_data='/start')]]
    if skip:
        custom_keyboard.append([InlineKeyboardButton('Пропустить', callback_data='/skip')])
    return InlineKeyboardMarkup(
        inline_keyboard=custom_keyboard,
        resize_keyboard=True
    )


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


def get_payment_menu(value):
    custom_keyboard = [
        [InlineKeyboardButton('Оплатить', callback_data=value)],
        [InlineKeyboardButton('Вернуться в меню', callback_data='/start')]
    ]
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


def get_delivery_buttons(delivery: bool = True, pickup: bool = True):
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


def create_cart_msg(update: Update, context: CallbackContext, delivery_address=None):
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
                <b>Телефон заказчика: {context.user_data[f'{login_user}_data']['phone']}</b>
                '''
    return summary_msg, custom_keyboard, total_value
