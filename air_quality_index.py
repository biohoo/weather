import requests
import pandas as pd
import json
from get_location import Location
import keyring

import plotly.express as px

class AirQualityAPI:
    '''Communicates with the air quality management district (AQMD)
     server and returns air quality information
     '''

    def __init__(self, location):
        self.url = f'https://api.waqi.info/feed/'
        self.token = keyring.get_password('Air Quality API','https://api.waqi.info/feed/')

        self.aqi_to_level = {range(0,50):       ['Good', 'rgb(68,204,0)'],
                             range(51,100):     ['Moderate','rgb(230,230,0)'],
                             range(101,150):    ['Unhealthy for Sensitive Groups','rgb(255,128,0)'],
                             range(151,200):    ['Unhealthy','rgb(255,42,0)'],
                             range(201, 300):   ['Very Unhealthy','rgb(153,0,153)'],
                             range(300,1000):   ['Hazardous','rgb(0,0,0)']}

        self.response = self.get_response(location)


    def get_response(self, location):
        url = self.url + f'{location}/?token={self.token}'
        response = requests.get(url).json()

        return response

    def get_health_rating(self):

        for key in self.aqi_to_level:
            if self.response['data']['aqi'] in key:

                return self.aqi_to_level[key]

    def get_forecast(self):
        df_dict = {}
        for key, value in self.response['data']['forecast']['daily'].items():
            df = pd.read_json(json.dumps(value))
            df_dict[key] = df

        return df_dict

    def graph_forecast(self):

        df_dict = self.get_forecast()

        summary = pd.DataFrame()


        for key, dataframe in df_dict.items():
            dataframe['pollutant'] = key
            summary = summary.append(dataframe)

        fig = px.line(summary, x='day', y='avg',
                                error_y='max', error_y_minus='min',
                                facet_row="pollutant",color='pollutant', title='Pollutants Forecast')
        fig.update_yaxes(matches=None)
        fig.show()
        fig.write_image('today_pollutants_forecast.jpg')

        print(summary)


if __name__ == '__main__':

    location = Location()
    city = location.geolocation_dict['city']
    print('returning air quality for ',city)
    airQuality = AirQualityAPI(city)

    print(airQuality.graph_forecast())
    print(airQuality.response['data']['aqi'], airQuality.response['data']['dominentpol'])
    print(airQuality.get_health_rating())

    air_quality_index = airQuality.response['data']['aqi']
