import requests
import os


FACEBOOK_TOKEN = os.environ["PAGE_ACCESS_TOKEN"]


def get_button_template(recipient_id, text, buttons):
    url = 'https://graph.facebook.com/v2.6/me/messages'
    params = {'access_token': FACEBOOK_TOKEN}
    headers = {'Content-Type': 'application/json'}
    json_data = {
        'recipient': {
            'id': recipient_id
        },
        'message': {
            'attachment': {
                'type': 'template',
                'payload': {
                    'template_type': 'button',
                    'text': text,
                    'buttons': buttons
                }
            }
        }
    }
    response = requests.post(url=url, params=params, headers=headers, json=json_data)
    response.raise_for_status()


def get_generic_template(recipient_id, elements):
    url = 'https://graph.facebook.com/v2.6/me/messages'
    params = {'access_token': FACEBOOK_TOKEN}
    headers = {'Content-Type': 'application/json'}
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
    response = requests.post(url=url, params=params, headers=headers, json=json_data)
    response.raise_for_status()
