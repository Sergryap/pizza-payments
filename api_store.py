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
        pprint(token_data)


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


def get_products():
    url = 'https://api.moltin.com/catalog/products'
    headers = {'Authorization': f'Bearer {os.environ["ACCESS_TOKEN"]}'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def get_product(product_id):
    url = f'https://api.moltin.com/catalog/products/{product_id}'
    headers = {'Authorization': f'Bearer {os.environ["ACCESS_TOKEN"]}'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def create_relationships_to_products(
        products,
        hierarchy_id='7a28da5f-9135-47d5-8467-5c37c133febb',
        node_id='135277f5-71c3-44c2-baed-3cb52a5b64c2'
):
    url = f'https://api.moltin.com/pcm/hierarchies/{hierarchy_id}/nodes/{node_id}/relationships/products'
    headers = {
        'Authorization': f'Bearer {os.environ["ACCESS_TOKEN"]}',
        'Content-Type': 'application/json',
    }
    json_data = {'data': []}
    for product in products['data']:
        print(product['id'])
        json_data['data'].append(
            {
                'type': 'product',
                'id': product['id']
            }
        )
    response = requests.post(url, headers=headers, json=json_data)
    response.raise_for_status()
    return response.json()


def get_pcm_products():
    url = 'https://api.moltin.com/pcm/products'
    headers = {'Authorization': f'Bearer {os.environ["ACCESS_TOKEN"]}'}
    params = {'include': 'component_products'}
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


def get_pcm_price_book(price_book_id):
    url = f'https://api.moltin.com/pcm/pricebooks/{price_book_id}'
    headers = {'Authorization': f'Bearer {os.environ["ACCESS_TOKEN"]}'}
    params = {'include': 'prices'}
    response = requests.get(url, headers=headers, params=params)
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


def created_string_fields(flow_id, flows_data):
    for flow_data in flows_data:
        create_field(
            name=flow_data['name'],
            description=flow_data['description'],
            field_type='string',
            flow_id=flow_id,
            order=flow_data['order']
        )


def created_float_fields(flow_id, flows_data):
    for flow_data in flows_data:
        create_field(
            name=flow_data['name'],
            description=flow_data['description'],
            field_type='float',
            flow_id=flow_id,
            order=flow_data['order'],
            validation_rules=flow_data['validation_rules']
        )


def create_entry(flow_slug, fields_data):
    url = f'https://api.moltin.com/v2/flows/{flow_slug}/entries'
    headers = {
        'Authorization': f'Bearer {os.environ["ACCESS_TOKEN"]}',
        'Content-Type': 'application/json'
    }
    json_data = {
        'data': {
            'type': 'entry'
        }
    }
    for field_slug, field_value in fields_data.items():
        json_data['data'].update({field_slug: field_value})
    response = requests.post(url=url, headers=headers, json=json_data)
    response.raise_for_status()
    return response.json()


def create_entry_relationship(flow_slug, entry_id, field_slug, resource_type, resource_id):
    url = f'https://api.moltin.com/v2/flows/{flow_slug}/entries/{entry_id}/relationships/{field_slug}'
    headers = {
        'Authorization': f'Bearer {os.environ["ACCESS_TOKEN"]}',
        'Content-Type': 'application/json'
    }
    json_data = {
        'data': [
            {
                'type': resource_type,
                'id': resource_id
            }
        ]
    }
    response = requests.post(url=url, headers=headers, json=json_data)
    response.raise_for_status()
    return response.json()


def get_file(file_id):
    url = f'https://api.moltin.com/v2/files/{file_id}'
    headers = {'Authorization': f'Bearer {os.environ["ACCESS_TOKEN"]}'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def create_cart(name, description='pizza-order'):
    url = 'https://api.moltin.com/v2/carts'
    headers = {
        'Authorization': f'Bearer {os.environ["ACCESS_TOKEN"]}',
        'Content-Type': 'application/json',
    }
    json_data = {
        'data': {
            'name': name,
            'description': description
        }
    }
    response = requests.post(url, headers=headers, json=json_data)
    response.raise_for_status()
    return response.json()


def get_cart(reference):
    url = f'https://api.moltin.com/v2/carts/{reference}'
    headers = {
        'Authorization': f'Bearer {os.environ["ACCESS_TOKEN"]}',
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def get_cart_items(reference):
    url = f'https://api.moltin.com/v2/carts/{reference}/items'
    headers = {
        'Authorization': f'Bearer {os.environ["ACCESS_TOKEN"]}',
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def remove_cart_item(reference, product_id):
    url = f'https://api.moltin.com/v2/carts/{reference}/items/{product_id}'
    headers = {'Authorization': f'Bearer {os.environ["ACCESS_TOKEN"]}'}
    response = requests.delete(url, headers=headers)
    response.raise_for_status()
    return response.json()


def add_product_to_cart(product_id, quantity, reference):
    url = f'https://api.moltin.com/v2/carts/{reference}/items'
    headers = {
        'Authorization': f'Bearer {os.environ["ACCESS_TOKEN"]}',
        'Content-Type': 'application/json',
    }
    json_data = {
        'data': {
            'id': product_id,
            'type': 'cart_item',
            'quantity': quantity,
        }
    }
    response = requests.post(url=url, headers=headers, json=json_data)
    response.raise_for_status()
    return response.json()


def create_customer(name, email, password=None):
    url = 'https://api.moltin.com/v2/customers'
    headers = {
        'Authorization': f'Bearer {os.environ["ACCESS_TOKEN"]}',
        'Content-Type': 'application/json'
    }

    data = {
        'type': 'customer',
        'name': name,
        'email': email,
        'password': password,
    }
    json_data = {
        'data': {key: value for key, value in data.items() if value is not None}
    }
    response = requests.post(url, headers=headers, json=json_data)
    response.raise_for_status()
    return response.json()


def create_customer_address(customer_id, first_name, address):
    url = f'https://api.moltin.com/v2/customers/{customer_id}/addresses'
    headers = {
        'Authorization': f'Bearer {os.environ["ACCESS_TOKEN"]}',
        'Content-Type': 'application/json'
    }
    json_data = {
        'data': {
            'type': 'address',
            'first_name': first_name,
            'last_name': '-',
            'line_1': address,
            'county': '-',
            'country': 'RU',
            'postcode': '-',
            'city': '-'
        }
    }
    response = requests.post(url, headers=headers, json=json_data)
    response.raise_for_status()
    return response.json()


def get_all_customers(email=None):
    url = 'https://api.moltin.com/v2/customers'
    headers = {'Authorization': f'Bearer {os.environ["ACCESS_TOKEN"]}'}
    params = {'filter': f'eq(email,{email})'} if email else ''
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


def get_all_entries(flow_slug='branch-addresses'):
    url = f'https://api.moltin.com/v2/flows/{flow_slug}/entries'
    headers = {'Authorization': f'Bearer {os.environ["ACCESS_TOKEN"]}'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def get_entry_by_email(email, flow_slug='customer-address'):
    all_entries = get_all_entries(flow_slug=flow_slug)
    return list((entry for entry in all_entries['data'] if entry['email'] == email))


def get_entry_by_pos(email: str, customer_pos: tuple, flow_slug='customer-address'):
    all_entries = get_all_entries(flow_slug=flow_slug)
    return list(
        (
            entry for entry in all_entries['data']
            if (entry['latitude'], entry['longitude']) == customer_pos
            and entry['email'] == email.lower().strip()
        )
    )


if __name__ == '__main__':
    env = Env()
    env.read_env()
    check_token()
    pprint(get_entry_by_pos(email='rs1180@mail.ru', customer_pos=(55.755819, 37.617644)))
    # pprint(get_all_entries(flow_slug='customer-address'))
    # pprint(get_entry_by_email(email='rs1180@mail.ru'))
    # pprint(create_customer_address(
    #     'cd2edb2c-f4ac-44a4-89dd-5822882db67a',
    #     'Sergey',
    #     'Пермь, ул. Целинная, 31/3'
    # ))
    # pprint(get_all_customers())
    # pprint(get_all_entries(flow_slug='customer-address'))
    # pprint(get_all_customers())
    # pprint(create_entry_relationship(
    #     flow_slug='customer-address',
    #     field_slug='customer',
    #     entry_id='f57b8e87-e3e4-46f0-a66c-05d13b9b5e7a',
    #     resource_id='edfb0885-9460-49de-9e3a-134b9e421033',
    #     resource_type='customer'
    # ))
    # pprint(get_all_entries())
    # all_products = get_pcm_products()
    # pprint(create_relationships_to_products(all_products))
    # pprint(get_products())
    # pprint(get_product('0f7dcda1-79bf-407c-80ea-49d22a1534e4'))
    # pprint(get_pcm_price_book(os.environ["PRICE_BOOK_ID"]))
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
    # created_string_fields(
    #     flow_id='40a7fb8f-fc3b-42be-bd26-c2f3648b96a2',
    #     flows_data=[
    #         {
    #             'name': 'Address',
    #             'description': 'Branch address',
    #             'order': 1
    #         },
    #         {
    #             'name': 'Alias',
    #             'description': 'Alias of branch address',
    #             'order': 2
    #         },
    #     ]
    # )
    # created_float_fields(
    #     flow_id='40a7fb8f-fc3b-42be-bd26-c2f3648b96a2',
    #     flows_data=[
    #         {
    #             'name': 'Longitude',
    #             'description': 'Longitude of branch address',
    #             'order': 3,
    #             'validation_rules': [
    #                 {
    #                     'type': 'between',
    #                     'options': {
    #                         'from': -180.0,
    #                         'to': 180.0
    #                     }
    #                 }
    #             ]
    #         },
    #         {
    #             'name': 'Latitude',
    #             'description': 'Latitude of branch address',
    #             'order': 4,
    #             'validation_rules': [
    #                 {
    #                     'type': 'between',
    #                     'options': {
    #                         'from': -90.0,
    #                         'to': 90.0
    #                     }
    #                 }
    #             ]
    #         }
    #     ]
    # )
    # pprint(
    #     create_field(
    #         name='Longitude',
    #         description='Longitude of Branch address',
    #         field_type='float',
    #         flow_id='40a7fb8f-fc3b-42be-bd26-c2f3648b96a2',
    #         order=3,
    #         validation_rules=[
    #             {
    #                 'type': 'between',
    #                 'options': {
    #                     'from': -180.0,
    #                     'to': 180.0
    #                 }
    #             }
    #         ]
    #     )
    # )
    # pprint(
    #     create_field(
    #         name='Latitude',
    #         description='Latitude of Branch address',
    #         field_type='float',
    #         flow_id='40a7fb8f-fc3b-42be-bd26-c2f3648b96a2',
    #         order=4,
    #         validation_rules=[
    #             {
    #                 'type': 'between',
    #                 'options': {
    #                     'from': -90.0,
    #                     'to': 90.0
    #                 }
    #             }
    #         ]
    #     )
    # )
