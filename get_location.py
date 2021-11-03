import requests
import json
from dateutil import tz
from datetime import datetime, timedelta

class Location:

    def __init__(self):
        self.ip = requests.get('http://ifconfig.me').text
        self.geolocation_response = requests.get(f'https://freegeoip.app/json/{self.ip}')
        self.geolocation_text = self.geolocation_response.text
        self.geolocation_dict = json.loads(self.geolocation_text)
        self.pretty_print_json_text = json.dumps(self.geolocation_dict, indent=4, sort_keys=True)

        self.local_time_converter = tz.tzlocal()
        self.utc_time_converter = tz.tzutc()

        self.local_time = datetime.now()
        self.utc_time = datetime.now(self.utc_time_converter)

    def __str__(self):
        city = self.geolocation_dict['city']
        region = self.geolocation_dict['region_name']
        hour, minute = self.local_time.hour, self.local_time.minute
        timezone = self.geolocation_dict['time_zone']

        statement = f'''  
        You are in the area of {city} within {region}.
        
        The time is now {hour}:{minute} {timezone} timezone.
        It is UTC {self.utc_time}
        {self.utc_time.replace(tzinfo=None) - self.local_time.replace(tzinfo=None)} hours ahead.
        '''
        return statement

if __name__ == '__main__':
    l = Location()
    ld = l.geolocation_dict

    print(ld)

    print(l)