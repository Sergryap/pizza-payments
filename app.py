import os
import re
import redis
import api_store as api

import requests
from flask import Flask, request

app = Flask(__name__)
FACEBOOK_TOKEN = os.environ["PAGE_ACCESS_TOKEN"]

database_password = os.environ['DATABASE_PASSWORD']
database_host = os.environ['DATABASE_HOST']
database_port = os.environ['DATABASE_PORT']
db = redis.Redis(host=database_host, port=int(database_port), password=database_password)


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
                    sender_id = messaging_event['sender']['id']
                    recipient_id = messaging_event['recipient']['id']
                    message_text = messaging_event['message']['text']

                    handle_users_reply(sender_id, message_text)
                elif messaging_event.get('postback'):
                    sender_id = messaging_event['sender']['id']
                    recipient_id = messaging_event['recipient']['id']
                    message_text = messaging_event['postback']['payload']
                    handle_users_reply(sender_id, message_text)

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


def handle_start(recipient_id, node_id=os.environ['FRONT_PAGE_NODE_ID']):
    pattern = re.compile(r'\b\w{8}-\w{4}-\w{4}-\w{4}-\w{12}')
    node_id_verify = bool(pattern.match(node_id))
    node_id = node_id if node_id_verify else os.environ['FRONT_PAGE_NODE_ID']
    products = api.get_products()['data']
    node_products = api.get_node_products(
        os.environ['HIERARCHY_ID'],
        node_id
    )
    node_product_ids = [product['id'] for product in node_products['data']]
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
    for product in products:
        if product['id'] in node_product_ids:
            main_image_id = product['relationships']['main_image']['data']['id']
            link_image = api.get_file(file_id=main_image_id)['data']['link']['href']
            elements.append(
                {
                    'title': f'{product["attributes"]["name"]} ({product["attributes"]["price"]["RUB"]["amount"]} р.)',
                    'image_url': link_image,
                    'subtitle': product['attributes'].get('description', ''),
                    'buttons': [
                        {
                            'type': 'postback',
                            'title': 'Добавить в корзину',
                            'payload': product['id'],
                        }
                    ]
                },
            )
    elements.append(
        {
            'title': 'Не нашли нужную пиццу?',
            'image_url': 'https://starburger-serg.store/images/finaly-pizza.jpg',
            'subtitle': 'Остальные можно посмотреть в одной из категорий',
            'buttons': [
                {
                    'type': 'postback',
                    'title': 'Особые',
                    'payload': '07f5eb2c-815e-41c9-be78-a41b985dd430',
                },
                {
                    'type': 'postback',
                    'title': 'Сытные',
                    'payload': '18557b54-9f75-4ce3-92e1-637c402100aa',
                },
                {
                    'type': 'postback',
                    'title': 'Острые',
                    'payload': '6111eb37-d408-40aa-a7d1-87cfbc17e044',
                },
            ]
        },
    )
    json_data = {
        'recipient': {
            'id': recipient_id,
        },
        'message': {
            'attachment': {
                'type': 'template',
                'payload': {
                    'template_type': 'generic',
                    'elements': elements
                },
            },
        },
    }
    url = 'https://graph.facebook.com/v2.6/me/messages'
    params = {'access_token': FACEBOOK_TOKEN}
    headers = {'Content-Type': 'application/json'}
    response = requests.post(
        url=url,
        params=params, headers=headers, json=json_data
    )
    response.raise_for_status()

    return 'START'


def handle_users_reply(sender_id, message_text):
    states_functions = {
        'START': handle_start,
        # 'HANDLE_MENU': send_product_info,
        # 'HANDLE_DESCRIPTION': handle_description,
        # 'CART_INFO': get_cart_info,
        # 'HANDLER_CART':  handler_cart,
        # 'HANDLE_EMAIL': handle_email,
        # 'HANDLE_PHONE': handle_phone,
        # 'HANDLE_LOCATION': handle_location,
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
    next_state = state_handler(sender_id, message_text)
    db.set(f'facebookid_{sender_id}', next_state)


if __name__ == '__main__':
    app.run(debug=True)
