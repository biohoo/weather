import requests
import json


class Location:

    def __init__(self):
        self.ip = requests.get('http://ifconfig.me').text
        self.geolocation_response = requests.get(f'https://freegeoip.app/json/{self.ip}')
        self.geolocation_text = self.geolocation_response.text
        self.geolocation_dict = json.loads(self.geolocation_text)
        self.pretty_print_json_text = json.dumps(self.geolocation_dict, indent=4, sort_keys=True)

        print(self.pretty_print_json_text)


if __name__ == '__main__':
    Location()