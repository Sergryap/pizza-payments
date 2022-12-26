import json
from pprint import pprint


def upload_file(file):
    with open(file, "r", encoding='utf-8') as file:
        data = file.read()
    return json.loads(data)


if __name__ == '__main__':
    pprint(upload_file('addresses.json'))
    pprint(upload_file('menu.json'))
