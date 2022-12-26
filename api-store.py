import os
import time
import requests

from environs import Env


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


if __name__ == '__main__':
    env = Env()
    env.read_env()
    check_token()
    print(os.environ['ACCESS_TOKEN'])
