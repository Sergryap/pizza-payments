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
    # upload_products()
    upload_addresses()
