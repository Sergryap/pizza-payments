import requests
from geopy import distance
from api_store import get_all_entries


def fetch_coordinates(apikey, address):
    base_url = 'https://geocode-maps.yandex.ru/1.x'
    response = requests.get(base_url, params={
        'geocode': address,
        'apikey': apikey,
        'format': 'json',
    })
    response.raise_for_status()
    found_places = response.json()['response']['GeoObjectCollection']['featureMember']

    if not found_places:
        return None

    most_relevant = found_places[0]
    lng, lat = most_relevant['GeoObject']['Point']['pos'].split(" ")

    return float(lat), float(lng)


def get_min_distance_branch(client_pos):
    branches = get_all_entries()
    branch_distances = []
    for branch in branches['data']:
        branch_pos = (branch['latitude'], branch['longitude'])
        dist = distance.distance(client_pos, branch_pos).km
        branch_distances.append(
            {'address': branch['address'], 'dist': dist}
        )
    branch_distances.sort(key=lambda x: x['dist'])
    selected_branch = branch_distances[0]

    return selected_branch['address'], selected_branch['dist']
