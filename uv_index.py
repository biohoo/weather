import requests
import pandas as pd
from datetime import datetime
from get_location import Location
import keyring

import plotly.graph_objects as go
from air_quality_index import AirQualityAPI

import sweetviz as sv


class APIQuotaReachedException(Exception):
    pass


class UVIndexAPI:
    def __init__(self):
        self.realtimeURL = 'https://api.openuv.io/api/v1/uv'
        self.forecastURL = 'https://api.openuv.io/api/v1/forecast'

        self.token = keyring.get_password('OpenUV API Key','openuvapi')
        self.header = {'x-access-token':self.token}
        self.latitude, self.longitude, self.altitude = (34.27, -118.83, 270)

        self.full_forecast = self.get_forecast()
        self.full_response = self.get_realtime_response()

    def set_token(self, new_token):
        '''
        Token has a max of 50 calls per day.  If needed, grab a new token from the service and
        set Mac Keychain here.
        '''

        keyring.set_password('OpenUV API Key','openuvapi', password=new_token)


    def set_location_and_altitude(self, latitude, longitude, altitude):

        self.latitude, self.longitude, self.altitude = (latitude, longitude, altitude)


    def get_realtime_response(self):
        '''Altitude correction factor in meters.  Based on Thousand Oaks.'''

        payload = {'lat':self.latitude, 'lng':self.longitude, 'alt':self.altitude}
        response = requests.get(url=self.realtimeURL, headers=self.header, params=payload)

        if 'error' in response.json():
            raise APIQuotaReachedException(response.json()['error'])

        return response.json()


    def get_forecast(self):
        '''Returns latest forecast for the day.'''

        payload = {'lat': self.latitude, 'lng': self.longitude, 'alt': self.altitude}
        response = requests.get(url=self.forecastURL, headers=self.header, params=payload)

        return response.json()


    def get_uv_index(self):
        '''Returns today's latest realtime-measured UV index.'''

        return self.full_response['result']['uv']


    def get_forecasted_uv_indices(self):
        '''Returns a dataframe of uv indices'''

        df = pd.DataFrame(self.get_forecast()['result'])

        df['uv_time'] = df['uv_time'].apply(lambda x: datetime.strptime(x, '%Y-%m-%dT%H:%M:%S.%fZ') # To datetime
                                            .replace(tzinfo=l.utc_time_converter)
                                            .astimezone(l.local_time_converter))

        df = pd.concat([df.drop(['sun_position'], axis=1),              #   Concatenate one with sun pos. dropped
                        df['sun_position'].apply(pd.Series)], axis=1)   #   with the sun position split by dict series.

        df['time'] = df['uv_time'].apply(lambda x : f'{x.strftime("%-I:%M %p")}')

        return df


    def get_safe_times(self, uv_max = 3.5):
        '''Return a dataframe filtered by UV index'''

        return self.get_forecasted_uv_indices()[self.get_forecasted_uv_indices()['uv'] < uv_max]


if __name__ == '__main__':
    l = Location()
    ld = l.geolocation_dict

    uv = UVIndexAPI()
    uv.set_location_and_altitude(latitude=ld['latitude'], longitude=ld['longitude'], altitude=0)
    index = uv.get_uv_index()
    print(index)

    whole_df = uv.get_forecasted_uv_indices()
    safe_times = uv.get_safe_times()

    DANGEROUS_UV, MODERATE_UV = 5, 3

    extended_cutoffs = whole_df[whole_df['uv'] > MODERATE_UV]
    strict_cutoffs = whole_df[whole_df['uv'] > DANGEROUS_UV]

    airQuality = AirQualityAPI(ld['city'])
    air_quality_index = airQuality.response['data']['aqi']
    air_quality_rating, air_quality_color = airQuality.get_health_rating()

    fig = go.Figure(layout_yaxis_range=[0,11])

    fig.add_trace(
        go.Scatter(
            mode='markers',
            x=uv.get_forecasted_uv_indices().time,
            y=uv.get_forecasted_uv_indices().uv,
            marker=dict(
                color='darkred',
                size=20
            ),
            showlegend=False
        )
    )


    fig.add_trace(
        go.Scatter(
            mode='markers',
            x=safe_times.time,
            y=safe_times.uv,
            marker=dict(
                color='rgb(51,85,255)',
                size=[50 if x < MODERATE_UV else 10 for x in safe_times.uv]
            ),
            showlegend=False
        )
    )

    fig.update_layout(
        title = f"UV over Time<br>City: {ld['city']}<br><b>{datetime.strftime(datetime.today(), '%d %b %Y')}</b>",
        xaxis_title="Time",
        yaxis_title="UV Index",
        font=dict(
            family="Courier New, monospace",
            size=18,
            color="RebeccaPurple"
        ),
        plot_bgcolor=air_quality_color,
        annotations = [dict(xref='x',
                            yref='y',
                            x='12:00 AM', y=0.5,
                            showarrow=False,
                            text =f'Air Quality: <b>{air_quality_index}</b> <br>({air_quality_rating})'
                            )]
    )

    fig.write_html('today_uv.html')
    fig.write_image('today_uv.jpg')

    sweetviz = sv.analyze(whole_df)
    sweetviz.show_html()

    airQuality.graph_forecast()

    fig.show()