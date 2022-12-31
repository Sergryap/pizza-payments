import os
import time
import requests

from environs import Env
from slugify import slugify
from pprint import pprint


def check_token(error=False):
    if not os.environ.get('TOKEN_EXPIRES') or int(os.environ['TOKEN_EXPIRES']) < int(time.time()) or error:
        url = 'https://api.moltin.com/oauth/access_token'
        client_id = os.getenv('CLIENT_ID')
        client_secret = os.getenv('CLIENT_SECRET')
        data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'client_credentials'
        }
        response = requests.post(url, data)
        response.raise_for_status()
        token_data = response.json()
        os.environ['TOKEN_EXPIRES'] = str(token_data['expires'] - 60)
        os.environ['ACCESS_TOKEN'] = token_data['access_token']
        print(token_data)


def create_product(name: str, sku: str, description: str, price: int):
    url = 'https://api.moltin.com/v2/products'
    headers = {
        'Authorization': f'Bearer {os.environ["ACCESS_TOKEN"]}',
        'Content-Type': 'application/json'
    }
    json_data = {
        'data': {
            'type': 'product',
            'name': name,
            'slug': slugify(name),
            'sku': sku,
            'manage_stock': False,
            'description': description,
            'price': [
                {
                    'amount': price,
                    'currency': 'RUB',
                    'includes_tax': True
                }
            ],
            'status': 'live',
            'commodity_type': 'physical'
        }
    }
    response = requests.post(url=url, headers=headers, json=json_data)
    response.raise_for_status()
    return response.json()


def create_pcm_product(name: str, sku: str, description: str):
    url = 'https://api.moltin.com/pcm/products'
    headers = {
        'Authorization': f'Bearer {os.environ["ACCESS_TOKEN"]}',
        'Content-Type': 'application/json'
    }
    json_data = {
        'data': {
            'type': 'product',
            'attributes': {
                'name': name,
                'commodity_type': 'physical',
                'sku': sku,
                'slug': slugify(name),
                'description': description,
                'status': 'live',
            },
        }
    }
    response = requests.post(url=url, headers=headers, json=json_data)
    response.raise_for_status()
    return response.json()


def add_product_price(price_book_id: str, sku: str, price: int):
    url = f'https://api.moltin.com/pcm/pricebooks/{price_book_id}/prices'
    headers = {
        'Authorization': f'Bearer {os.environ["ACCESS_TOKEN"]}',
        'Content-Type': 'application/json'
    }
    json_data = {
        'data': {
            'type': 'product-price',
            'attributes': {
                'sku': sku,
                'currencies': {
                    'RUB': {
                        'amount': price,
                        'includes_tax': True,
                    }
                }
            }
        }
    }
    response = requests.post(url=url, headers=headers, json=json_data)
    response.raise_for_status()
    return response.json()


def upload_image_url(file_location):
    url = 'https://api.moltin.com/v2/files'
    headers = {
        'Authorization': f'Bearer {os.environ["ACCESS_TOKEN"]}'
    }
    files = {
        'file_location': (None, file_location),
    }
    response = requests.post(url, headers=headers, files=files)
    response.raise_for_status()
    return response.json()


def create_main_image_relationship(product_id, image_id):
    url = f'https://api.moltin.com/pcm/products/{product_id}/relationships/main_image'
    headers = {
        'Authorization': f'Bearer {os.environ["ACCESS_TOKEN"]}',
        'Content-Type': 'application/json'
    }
    json_data = {
        'data': {
            'type': 'file',
            'id': image_id
        }
    }
    response = requests.post(url=url, headers=headers, json=json_data)
    response.raise_for_status()


def get_pcm_products():
    url = 'https://api.moltin.com/pcm/products'
    headers = {'Authorization': f'Bearer {os.environ["ACCESS_TOKEN"]}'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def create_flow(name, description, enabled=True):  # 'id': '40a7fb8f-fc3b-42be-bd26-c2f3648b96a2'
    url = 'https://api.moltin.com/v2/flows'
    headers = {
        'Authorization': f'Bearer {os.environ["ACCESS_TOKEN"]}',
        'Content-Type': 'application/json'
    }
    json_data = {
        'data': {
            'type': 'flow',
            'name': name,
            'slug': slugify(name),
            'description': description,
            'enabled': enabled
        }
    }
    response = requests.post(url=url, headers=headers, json=json_data)
    response.raise_for_status()
    return response.json()


def delete_flow(flow_id):
    url = f'https://api.moltin.com/v2/flows/{flow_id}'
    headers = {'Authorization': f'Bearer {os.environ["ACCESS_TOKEN"]}'}
    response = requests.delete(url=url, headers=headers)
    response.raise_for_status()


def create_field(
        name,
        description,
        field_type,
        flow_id,
        order,
        validation_rules=None,
        required=True,
        enabled=True
):
    url = 'https://api.moltin.com/v2/fields'
    headers = {
        'Authorization': f'Bearer {os.environ["ACCESS_TOKEN"]}',
        'Content-Type': 'application/json'
    }
    json_data = {
        'data': {
            'type': 'field',
            'name': name,
            'slug': slugify(name),
            'field_type': field_type,
            'description': description,
            'required': required,
            'enabled': enabled,
            'order': order,
            'relationships': {
                'flow': {
                    'data': {
                        'type': 'flow',
                        'id': flow_id
                    }
                }
            }
        }
    }
    if validation_rules:
        json_data['data'].update({'validation_rules': validation_rules})
    response = requests.post(url=url, headers=headers, json=json_data)
    response.raise_for_status()
    return response.json()


if __name__ == '__main__':
    env = Env()
    env.read_env()
    check_token()
    # pprint(
    #   create_flow(
    #       name='Branch addresses',
    #       description='Addresses of branches of pizzerias'
    #   )
    # )
    # delete_flow('63618de5-0fb8-46b9-9318-bb2019953135')
    # pprint(
    #     create_field(
    #         name='Address',
    #         description='Branch address',
    #         field_type='string',
    #         flow_id='40a7fb8f-fc3b-42be-bd26-c2f3648b96a2',
    #         order=1
    #     )
    # )
    # pprint(
    #     create_field(
    #         name='Alias',
    #         description='Alias of Branch address',
    #         field_type='string',
    #         flow_id='40a7fb8f-fc3b-42be-bd26-c2f3648b96a2',
    #         order=2
    #     )
    # )
    pprint(
        create_field(
            name='Longitude',
            description='Longitude of Branch address',
            field_type='float',
            flow_id='40a7fb8f-fc3b-42be-bd26-c2f3648b96a2',
            order=3,
            validation_rules=[
                {
                    'type': 'between',
                    'options': {
                        'from': -180.0,
                        'to': 180.0
                    }
                }
            ]
        )
    )
    pprint(
        create_field(
            name='Latitude',
            description='Latitude of Branch address',
            field_type='float',
            flow_id='40a7fb8f-fc3b-42be-bd26-c2f3648b96a2',
            order=4,
            validation_rules=[
                {
                    'type': 'between',
                    'options': {
                        'from': -90.0,
                        'to': 90.0
                    }
                }
            ]
        )
    )