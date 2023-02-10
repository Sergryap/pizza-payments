import os
import api_store as api

import requests
from flask import Flask, request

app = Flask(__name__)
FACEBOOK_TOKEN = os.environ["PAGE_ACCESS_TOKEN"]


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
    api.check_token()
    if data["object"] == "page":
        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:
                if messaging_event.get("message"):
                    sender_id = messaging_event["sender"]["id"]
                    recipient_id = messaging_event["recipient"]["id"]
                    message_text = messaging_event["message"]["text"]
                    send_message(sender_id, message_text)
                    send_menu(sender_id)

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


def send_menu(recipient_id):
    products = api.get_products()['data']
    first_element = [
        {
            'title': 'Меню',
            'image_url': 'https://starburger-serg.store/images/logo-pizza.png',
            'subtitle': 'Здесь выможете выбрать один из товаров',
            'buttons': [
                {
                    'type': 'postback',
                    'title': 'Корзина',
                    'payload': 'cart',
                },
                {
                    'type': 'postback',
                    'title': 'Акции',
                    'payload': 'action',
                },
                {
                    'type': 'postback',
                    'title': 'Сделать заказ',
                    'payload': 'order',
                },
            ]
        }
    ]
    elements = first_element.copy()
    several_json_data = []
    for number, product in enumerate(products, start=1):
        main_image_id = product['relationships']['main_image']['data']['id']
        link_image = api.get_file(file_id=main_image_id)['data']['link']['href']
        buttons = [
            {
                'type': 'postback',
                'title': 'Добавить в корзину',
                'payload': product['id'],
            }
        ]
        elements.append(
            {
                'title': f'{product["attributes"]["name"]} ({product["attributes"]["price"]["RUB"]["amount"]} р.)',
                'image_url': link_image,
                'subtitle': product['attributes'].get('description', ''),
                'buttons': buttons
            },
        )
        if number % 9 == 0 or number == len(products):
            several_json_data.append(
                {
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
            )
            elements = first_element.copy()

    url = "https://graph.facebook.com/v2.6/me/messages"
    params = {"access_token": FACEBOOK_TOKEN}
    headers = {"Content-Type": "application/json"}
    for json_data in several_json_data[:1]:
        response = requests.post(
            url=url,
            params=params, headers=headers, json=json_data
        )
        response.raise_for_status()


if __name__ == '__main__':
    app.run(debug=True)
