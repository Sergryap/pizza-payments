import os
import re
import redis
import api_store as api
import json

import requests
from flask import Flask, request
from textwrap import dedent
from geo_informer import fetch_coordinates, get_min_distance_branch
from api_fb import get_button_template, get_generic_template
from api_fb import FACEBOOK_TOKEN

app = Flask(__name__)

database_password = os.environ['DATABASE_PASSWORD']
database_host = os.environ['DATABASE_HOST']
database_port = os.environ['DATABASE_PORT']
db = redis.Redis(host=database_host, port=int(database_port), password=database_password)

THANK_TEXT = 'Спасибо. Мы свяжемся с Вами!'
GEO_REQUEST_TEXT = 'Для доставки вашего заказа пришлите нам ваш адрес текстом'
AFTER_EMAIL_TEXT = 'Либо вернитесь к выбору:'
DELIVERY_COST_1 = 100
DELIVERY_COST_2 = 300
AFTER_GEO_TEXT = 'Вы можете продолжить выбор, либо уточните адрес:'
REPIET_SEND_COORD = 'Извините, но мы не смогли определить ваши координаты!'
SPECIAL_NODE_ID = '07f5eb2c-815e-41c9-be78-a41b985dd430'
SATISFYING_NODE_ID = '18557b54-9f75-4ce3-92e1-637c402100aa'
SPICY_NODE_ID = '6111eb37-d408-40aa-a7d1-87cfbc17e044'
FRONT_PAGE_NODE_ID = 'd00bc494-5ecd-44f2-a943-2b46f745e200'


@app.route('/', methods=['GET'])
def verify():
    """
    При верификации вебхука у Facebook он отправит запрос на этот адрес. На него нужно ответить VERIFY_TOKEN.
    """
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == os.environ["VERIFY_TOKEN"]:
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200

    return "Hello world", 200


@app.route('/', methods=['POST'])
def webhook():
    """
    Основной вебхук, на который будут приходить сообщения от Facebook.
    """
    data = request.get_json()
    if data.get('object') == 'page':
        for entry in data['entry']:
            for messaging_event in entry['messaging']:
                if messaging_event.get('message'):
                    handle_users_reply(messaging_event)
                elif messaging_event.get('postback'):
                    handle_users_reply(messaging_event)
    elif data.get('triggered_by') == 'catalog-release.updated':
        for node_id in [FRONT_PAGE_NODE_ID, SPECIAL_NODE_ID, SATISFYING_NODE_ID, SPICY_NODE_ID]:
            get_product_elements(node_id, event=True)
    return "ok", 200


def send_message(recipient_id, message_text):
    params = {"access_token": FACEBOOK_TOKEN}
    headers = {"Content-Type": "application/json"}
    request_content = {
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message_text
        }
    }
    response = requests.post(
        "https://graph.facebook.com/v2.6/me/messages",
        params=params, headers=headers, json=request_content
    )
    response.raise_for_status()


def handle_start(recipient_id, message_text=FRONT_PAGE_NODE_ID, title=None):
    if title == 'Добавить в корзину':
        product_id, product_name = message_text.split('_')
        api.add_product_to_cart(
            product_id=product_id,
            quantity=1,
            reference=recipient_id
        )
        send_message(recipient_id, f'В корзину добавлена пицца {product_name}')
        return 'START'
    elif title == 'Корзина':
        return handler_cart(recipient_id)
    elif title == 'Сделать заказ':
        send_message(
            recipient_id,
            'Введите ваш email, либо продолжите выбор:'
        )
        get_button_template(
            recipient_id, 'Либо отмените ввод email, либо вернитесь в меню',
            buttons=[
                {
                    'type': 'postback',
                    'title': 'Отменить',
                    'payload': 'NEXT_STEP',
                },
                {
                    'type': 'postback',
                    'title': 'К меню',
                    'payload': '/start'
                }
            ]
        )
        return 'HANDLE_EMAIL'

    pattern_category = re.compile(r'\b\w{8}-\w{4}-\w{4}-\w{4}-\w{12}')
    node_id_verify = bool(pattern_category.match(message_text))
    node_id = message_text if node_id_verify else FRONT_PAGE_NODE_ID
    elements = [
        {
            'title': 'Меню',
            'image_url': 'https://starburger-serg.store/images/logo-pizza.png',
            'subtitle': 'Здесь вы можете выбрать один из товаров',
            'buttons': [
                {
                    'type': 'postback',
                    'title': 'Корзина',
                    'payload': 'CART',
                },
                {
                    'type': 'postback',
                    'title': 'Акции',
                    'payload': 'PROMOTION',
                },
                {
                    'type': 'postback',
                    'title': 'Сделать заказ',
                    'payload': 'ORDER',
                },
            ]
        }
    ]
    product_elements = get_product_elements(node_id)
    elements.extend(product_elements)
    elements.append(
        {
            'title': 'Не нашли нужную пиццу?',
            'image_url': 'https://starburger-serg.store/images/finaly-pizza.jpg',
            'subtitle': 'Остальные можно посмотреть в одной из категорий',
            'buttons': [
                {
                    'type': 'postback',
                    'title': 'Особые',
                    'payload': SPECIAL_NODE_ID,
                },
                {
                    'type': 'postback',
                    'title': 'Сытные',
                    'payload': SATISFYING_NODE_ID,
                },
                {
                    'type': 'postback',
                    'title': 'Острые',
                    'payload': SPICY_NODE_ID,
                },
            ]
        },
    )
    get_generic_template(recipient_id, elements)

    return 'START'


def get_product_elements(node_id, event=False):
    product_elements = db.get(node_id)
    if not product_elements or event:
        product_elements = []
        products = api.get_products()['data']
        node_products = api.get_node_products(os.environ['HIERARCHY_ID'], node_id)
        node_product_ids = [product['id'] for product in node_products['data']]
        for product in products:
            if product['id'] in node_product_ids:
                main_image_id = product['relationships']['main_image']['data']['id']
                link_image = api.get_file(file_id=main_image_id)['data']['link']['href']
                product_elements.append(
                    {
                        'title': f'{product["attributes"]["name"]} ({product["attributes"]["price"]["RUB"]["amount"]} р.)',
                        'image_url': link_image,
                        'subtitle': product['attributes'].get('description', ''),
                        'buttons': [
                            {
                                'type': 'postback',
                                'title': 'Добавить в корзину',
                                'payload': f"{product['id']}_{product['attributes']['name']}",
                            }
                        ]
                    },
                )
        db.set(node_id, json.dumps(product_elements))
    else:
        product_elements = json.loads(product_elements)

    return product_elements


def handler_cart(recipient_id, message_text=None, title=None):
    if title == 'К меню':
        return handle_start(recipient_id, message_text)
    elif title == 'Добавить еще одну':
        product_id, product_name = message_text.split('_')
        api.add_product_to_cart(
            product_id=product_id,
            quantity=1,
            reference=recipient_id
        )
        send_message(recipient_id, f'В корзину добавлена пицца {product_name}')
    elif title == 'Убрать из корзины':
        item_cart_id, product_name = message_text.split('_')
        api.remove_cart_item(recipient_id, item_cart_id)
        send_message(recipient_id, f'Пицца {product_name} удалена из корзины')
    # elif title == 'Доставка':
    #     pass
    # elif title == 'Самовывоз':
    #     pass
    total_value = (
        api.get_cart(recipient_id)
        ['data']['meta']['display_price']['without_tax']['formatted']
    )
    cart_items = api.get_cart_items(recipient_id)
    elements = [
        {
            'title': f'Ваш заказ на сумму {total_value}',
            'image_url': 'https://starburger-serg.store/images/cart.jpg',
            'subtitle': 'Выберите, чтобы вы хотели:',
            'buttons': [
                {
                    'type': 'postback',
                    'title': 'Самовывоз',
                    'payload': 'PICKUP',
                },
                {
                    'type': 'postback',
                    'title': 'Доставка',
                    'payload': 'DELIVERY',
                },
                {
                    'type': 'postback',
                    'title': 'К меню',
                    'payload': os.environ['FRONT_PAGE_NODE_ID'],
                },
            ]
        }
    ]
    for item in cart_items['data']:
        elements.append(
            {
                'title': f"{item['name']} ({item['quantity']} шт.)",
                'image_url': item['image']['href'],
                'subtitle': item['description'],
                'buttons': [
                    {
                        'type': 'postback',
                        'title': 'Добавить еще одну',
                        'payload': f"{item['product_id']}_{item['name']}",
                    },
                    {
                        'type': 'postback',
                        'title': 'Убрать из корзины',
                        'payload': f"{item['id']}_{item['name']}",
                    },
                ]
            },
        )
    get_generic_template(recipient_id, elements)

    return 'HANDLER_CART'


def handle_email(recipient_id, message_text=None, title=None):
    if message_text == 'NEXT_STEP':
        user_email = 'none@none.com'
    else:
        user_email = message_text.lower().strip()
    email_rule = re.compile(r'(^\S+@\S+\.\S+$)', flags=re.IGNORECASE)
    if email_rule.search(user_email):
        actual_return = 'HANDLE_PHONE'
        db.set(f'{recipient_id}_mail', user_email)
        msg = 'Введите Ваш телефон'
        try:
            customer = api.create_customer(f'facebookid_{recipient_id}', user_email)
            db.set(f'{recipient_id}_customer_id', customer['data']['id'])
        except requests.exceptions.HTTPError:
            found_user = api.get_all_customers(user_email)
            db.set(f'{recipient_id}_customer_id', found_user['data'][0].get('id'))
    else:
        msg = f'Введите корректный email'
        actual_return = 'HANDLE_EMAIL'
    send_message(recipient_id, msg)
    get_button_template(
        recipient_id, AFTER_EMAIL_TEXT,
        buttons=[
            {
                'type': 'postback',
                'title': 'К меню',
                'payload': '/start'
            }
        ]
    )

    return actual_return


def handle_phone(recipient_id, message_text=None, title=None):
    user_phone = message_text
    phone_rule = re.compile(r'(^[+0-9]{1,3})*([0-9]{10,11}$)')
    if phone_rule.search(user_phone):
        actual_return = 'HANDLE_LOCATION'
        db.set(f'{recipient_id}_phone', user_phone)
        msg = f'{THANK_TEXT}\n{GEO_REQUEST_TEXT}'
    else:
        actual_return = 'HANDLE_PHONE'
        msg = f'Введите корректный номер телефона'
    send_message(recipient_id, msg)
    get_button_template(
        recipient_id, AFTER_EMAIL_TEXT,
        buttons=[
            {
                'type': 'postback',
                'title': 'К меню',
                'payload': '/start'
            }
        ]
    )

    return actual_return


def handle_location(recipient_id, message_text=None, title=None):

    address = message_text
    current_pos = fetch_coordinates(os.environ['YANDEX_GEO_TOKEN'], address)

    if current_pos:
        branch_address, branch_dist, telegram_id = get_min_distance_branch(current_pos)
        user_email = db.get(f'{recipient_id}_mail').decode('utf-8')
        user_phone = db.get(f'{recipient_id}_phone').decode('utf-8')
        existing_entry = api.get_entry_by_pos(user_email, user_phone, current_pos)
        address = address if address else 'Пользователь не указал адрес'
        current_lat, current_lng = current_pos
        if not existing_entry:
            customer_address_entry = api.create_entry(
                flow_slug='customer-address',
                fields_data={
                    'address': address,
                    'email': user_email.lower().strip(),
                    'phone': user_phone,
                    'latitude': current_lat,
                    'longitude': current_lng
                }
            )
            api.create_entry_relationship(
                flow_slug='customer-address',
                entry_id=customer_address_entry['data']['id'],
                field_slug='customer',
                resource_type='customer',
                resource_id=db.get(f'{recipient_id}_customer_id').decode('utf-8')
            )
        if branch_dist <= 0.5:
            msg = f'''
                   Можете забрать пиццу из нашей пиццерии неподалеку?
                   Она всего в {round(branch_dist*1000, 0)} метров от Вас!
                   Вот её адрес: {branch_address}.
                   А можем и бесплатно доставить нам не сложно.
                   '''
            delivery_cost = 0
        elif branch_dist <= 5:
            msg = f'''
                   Похоже придется ехать до Вас на самокате.
                   Доставка будет стоить {DELIVERY_COST_1} р.
                   Доставляем или самовывоз?
                   '''
            delivery_cost = DELIVERY_COST_1
        elif branch_dist <= 20:
            msg = f'''
                   Похоже придется ехать до Вас на автомобиле.
                   Доставка будет стоить {DELIVERY_COST_2} р.
                   Доставляем или самовывоз?
                   '''
            delivery_cost = DELIVERY_COST_2
        elif branch_dist <= 50:
            msg = f'''
                   Простите но так далеко мы пиццу не доставляем.
                   Ближайшая пиццерия от Вас в {round(branch_dist, 0)} км.
                   Но вы может забрать её самостоятельно.
                   Оформляем самовывоз?
                   '''
            delivery_cost = 0
        else:
            msg = f'''
                   Простите но так далеко мы пиццу не доставляем.
                   Ближайшая пиццерия от Вас в {round(branch_dist, 0)} км.
                   Мы уверены, что есть другие пиццерии гораздо ближе.
                   Либо уточните адрес доставки.
                   '''
        msg = f'{dedent(msg)}\n{AFTER_GEO_TEXT}'
    else:
        msg = f'{THANK_TEXT}\n{REPIET_SEND_COORD}\n{AFTER_GEO_TEXT}'
    send_message(recipient_id, msg)
    if current_pos and branch_dist <= 50:
        api.checkout_cart(
            reference=recipient_id,
            customer_id=db.get(f'{recipient_id}_customer_id').decode('utf-8'),
            first_name='Test',
            last_name='Test',
            address=address,
            phone_number=db.get(f'{recipient_id}_phone').decode('utf-8')
        )
        return 'START'
    return 'START'


def handle_users_reply(messaging_event):
    sender_id = messaging_event['sender']['id']
    if messaging_event.get('message'):
        message_text = messaging_event['message']['text']
        title = None
    elif messaging_event.get('postback'):
        message_text = messaging_event['postback']['payload']
        title = messaging_event['postback']['title']
    else:
        return
    states_functions = {
        'START': handle_start,
        # 'HANDLE_MENU': send_product_info,
        # 'HANDLE_DESCRIPTION': handle_description,
        # 'CART_INFO': get_cart_info,
        'HANDLER_CART':  handler_cart,
        'HANDLE_EMAIL': handle_email,
        'HANDLE_PHONE': handle_phone,
        'HANDLE_LOCATION': handle_location,
        # 'HANDLE_DELIVERY': handle_delivery,
        # 'HANDLE_PAYMENT': handle_payment,
        # 'PRECHECKOUT': precheckout_callback,
    }
    recorded_state = db.get(f'facebookid_{sender_id}')
    if not recorded_state or recorded_state.decode("utf-8") not in states_functions.keys():
        user_state = "START"
    else:
        user_state = recorded_state.decode("utf-8")
    if message_text == "/start":
        user_state = "START"
    state_handler = states_functions[user_state]
    api.check_token()
    next_state = state_handler(sender_id, message_text, title)
    db.set(f'facebookid_{sender_id}', next_state)


if __name__ == '__main__':
    app.run(debug=True)
