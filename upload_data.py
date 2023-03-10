import json
import os
import api_store as api
import requests

from environs import Env


def upload_file(file):
    with open(file, "r", encoding='utf-8') as file:
        data = file.read()
    return json.loads(data)


def upload_products(file='menu.json'):
    products = upload_file(file)
    for product in products:
        print(f'Загружаю данные для {product["name"]}')
        try:
            created_product = api.create_pcm_product(
                name=product['name'],
                sku=str(product['id']),
                description=product['description']
            )
            api.add_product_price(
                price_book_id=os.environ['PRICE_BOOK_ID'],
                sku=str(product['id']),
                price=product['price']
            )
            image = api.upload_image_url(
                file_location=product['product_image']['url']
            )
            api.create_main_image_relationship(
                product_id=created_product['data']['id'],
                image_id=image['data']['id']
            )
        except requests.exceptions.HTTPError:
            continue


def upload_addresses(file='addresses.json', flow_slug='branch-addresses'):
    addresses = upload_file(file)
    for address in addresses:
        fields_data = {
            'address': address['address']['full'],
            'alias': address['alias'],
            'longitude': float(address['coordinates']['lon']),
            'latitude': float(address['coordinates']['lat'])
        }
        print(f'Загружаю данные для {address["address"]["full"]}')
        try:
            api.create_entry(flow_slug, fields_data)
        except requests.exceptions.HTTPError:
            continue


if __name__ == '__main__':
    env = Env()
    env.read_env()
    api.check_token()

    # Создание модели для адреса филиала
    branch_address_flow = api.create_flow(name='Branch addresses', description='Addresses of branches of pizzerias')
    branch_address_flow_id = branch_address_flow['data']['id']
    api.created_string_fields(
        flow_id=branch_address_flow_id,
        flows_data=[
            {
                'name': 'Address',
                'description': 'Branch address',
                'order': 1
            },
            {
                'name': 'Alias',
                'description': 'Alias of Branch address',
                'order': 2
            },
            {
                'name': 'Telegram ID',
                'description': 'The deliveryman pizza telegram id',
                'order': 5,
                'default': '1642719191'
            },
        ]
    )
    api.created_float_fields(
            flow_id=branch_address_flow_id,
            flows_data=[
                {
                    'name': 'Longitude',
                    'description': 'Longitude of branch address',
                    'order': 3,
                    'validation_rules': [
                        {
                            'type': 'between',
                            'options': {
                                'from': -180.0,
                                'to': 180.0
                            }
                        }
                    ]
                },
                {
                    'name': 'Latitude',
                    'description': 'Latitude of branch address',
                    'order': 4,
                    'validation_rules': [
                        {
                            'type': 'between',
                            'options': {
                                'from': -90.0,
                                'to': 90.0
                            }
                        }
                    ]
                }
            ]
        )

    # Cоздание модели для адреса пользователя
    customer_address_flow = api.create_flow(name='Customer address', description='Customer address')
    customer_address_flow_id = customer_address_flow['data']['id']
    api.created_string_fields(
            flow_id=customer_address_flow_id,
            flows_data=[
                {
                    'name': 'Address',
                    'description': 'Customer address',
                    'order': 1
                },
                {
                    'name': 'Email',
                    'description': 'Email customer address',
                    'order': 2
                },
                {
                    'name': 'Phone',
                    'description': 'Customer phone number',
                    'order': 3
                },
            ]
        )
    api.created_float_fields(
        flow_id=customer_address_flow_id,
        flows_data=[
            {
                'name': 'Latitude',
                'description': 'Latitude of customer address',
                'order': 4,
                'validation_rules': [
                    {
                        'type': 'between',
                        'options': {
                            'from': -90.0,
                            'to': 90.0
                        }
                    }
                ]
            },
            {
                'name': 'Longitude',
                'description': 'Longitude of customer address',
                'order': 5,
                'validation_rules': [
                    {
                        'type': 'between',
                        'options': {
                            'from': -180.0,
                            'to': 180.0
                        }
                    }
                ]
            },
        ]
    )
    api.create_field(
        name='Customer',
        description='Customer data relationship',
        field_type='relationship',
        flow_id=customer_address_flow_id,
        order=6,
        validation_rules=[
            {
                'type': 'one-to-many',
                'to': 'Customers'
            }
        ]
    )
    upload_products()
    upload_addresses()
