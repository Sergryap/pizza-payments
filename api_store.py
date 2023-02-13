import os
import time
import requests

from environs import Env
from slugify import slugify


def check_token():
    if not os.environ.get('TOKEN_EXPIRES') or int(os.environ['TOKEN_EXPIRES']) < int(time.time()):
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
        default=None,
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
    if default:
        json_data['data'].update({'default': default})
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
            order=flow_data['order'],
            default=flow_data.get('default', None)
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


def get_entry_by_pos(email: str, phone: str, customer_pos: tuple, flow_slug='customer-address'):
    all_entries = get_all_entries(flow_slug=flow_slug)
    return list(
        (
            entry for entry in all_entries['data']
            if (entry['latitude'], entry['longitude']) == customer_pos
            and entry['email'] == email.lower().strip()
            and entry['phone'] == phone
        )
    )


def checkout_cart(reference, customer_id, first_name, last_name, address, phone_number):
    url = f'https://api.moltin.com/v2/carts/{reference}/checkout'
    headers = {
        'Authorization': f'Bearer {os.environ["ACCESS_TOKEN"]}',
        'Content-Type': 'application/json'
    }
    json_data = {
        'data': {
            'customer': {
                'id': customer_id
            },
            'billing_address': {
                'first_name': first_name,
                'last_name': last_name,
                'line_1': address,
                'region': 'Russia',
                'postcode': '1',
                'country': 'RU'
            },
            'shipping_address': {
                'first_name': first_name,
                'last_name': last_name,
                'phone_number': phone_number,
                'line_1': address,
                'region': 'Russia',
                'postcode': '1',
                'country': 'RU'
            }
        }
    }
    response = requests.post(url, headers=headers, json=json_data)
    response.raise_for_status()
    return response.json()


def create_category(name, description):
    url = 'https://api.moltin.com/v2/categories'
    headers = {
        'Authorization': f'Bearer {os.environ["ACCESS_TOKEN"]}',
        'Content-Type': 'application/json'
    }
    json_data = {
        'data': {
            'type': 'category',
            'name': name,
            'slug': slugify(name),
            'description': description,
            'status': 'live'
        }
    }
    response = requests.post(url, headers=headers, json=json_data)
    response.raise_for_status()
    return response.json()


def get_node_products(hierarchy_id, node_id):
    url = f'https://api.moltin.com/pcm/hierarchies/{hierarchy_id}/nodes/{node_id}/products'
    headers = {'Authorization': f'Bearer {os.environ["ACCESS_TOKEN"]}'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def create_webhook_integration(webhook_url):
    url = 'https://api.moltin.com/v2/integrations'
    headers = {
        'Authorization': f'Bearer {os.environ["ACCESS_TOKEN"]}',
        'Content-Type': 'application/json'
    }
    json_data = {
        'data': {
            'type': 'integration',
            'name': 'Catalog',
            'description': 'Track сhanges in the сatalog',
            'enabled': True,
            'observes': [
                'catalog-release.updated',
            ],
            'integration_type': 'webhook',
            'configuration': {
                'url': webhook_url
            }
        }
    }
    response = requests.post(url, headers=headers, json=json_data)
    response.raise_for_status()
    return response.json()


if __name__ == '__main__':
    env = Env()
    env.read_env()
    check_token()
    create_webhook_integration('https://starburger-serg.store')
