import requests
import messaging.mac_messaging as msg
import pandas as pd
from datetime import datetime
from dateutil import tz
import questionary
from get_location import Location

import plotly.graph_objects as go
from air_quality_index import AirQualityAPI

import sweetviz as sv

from_zone = tz.tzutc()
to_zone = tz.tzlocal()

location = Location()

latitude, longitude = location.geolocation_dict['latitude'], location.geolocation_dict['longitude']
city = location.geolocation_dict['city']




class UVIndexAPI:
    def __init__(self):
        self.realtimeURL = 'https://api.openuv.io/api/v1/uv'
        self.forecastURL = 'https://api.openuv.io/api/v1/forecast'

        self.token = 'be162556db5b654875eff1bc5c706553'
        self.header = {'x-access-token':self.token}
        self.latitude, self.longitude, self.altitude = (34.27, -118.83, 270)

        self.full_forecast = self.get_forecast()
        self.full_response = self.get_realtime_response()
        #self.forecast_dataframe = self.get_forecasted_uv_indices()

    def set_token(self, new_token):
        '''
        Token has a max of 50 calls per day.

        Has the token expired?  Generate a new one and set it.
        If this is a common occurrence, set the token as an external file.
        '''
        self.token = new_token

    def set_location_and_altitude(self, latitude, longitude, altitude):

        self.latitude, self.longitude, self.altitude = (latitude, longitude, altitude)


    def get_realtime_response(self):
        '''Altitude correction factor in meters.  Based on Thousand Oaks.'''

        payload = {'lat':self.latitude, 'lng':self.longitude, 'alt':self.altitude}
        response = requests.get(url=self.realtimeURL, headers=self.header, params=payload)

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
                                            .replace(tzinfo=from_zone)  #   Explicitly state timezone = UTC
                                            .astimezone(to_zone))       #   Convert to local (PST)

        df = pd.concat([df.drop(['sun_position'], axis=1),              #   Concatenate one with sun pos. dropped
                        df['sun_position'].apply(pd.Series)], axis=1)   #   with the sun position split by dict series.

        df['time'] = df['uv_time'].apply(lambda x : f'{x.strftime("%-I:%M %p")}')

        return df


    def get_safe_times(self, uv_max = 3.5):
        '''Return a dataframe filtered by UV index'''

        return self.get_forecasted_uv_indices()[self.get_forecasted_uv_indices()['uv'] < uv_max]



uv = UVIndexAPI()
uv.set_location_and_altitude(latitude=latitude, longitude=longitude, altitude=0)
index = uv.get_uv_index()
print(index)

whole_df = uv.get_forecasted_uv_indices()
safe_times = uv.get_safe_times()

extended_cutoffs = whole_df[whole_df['uv'] > 3]
strict_cutoffs = whole_df[whole_df['uv'] > 5]


airQuality = AirQualityAPI(city)
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
            size=20
        ),
        showlegend=False
    )
)

fig.update_layout(
    title = f"UV over Time<br>City: {city}<br><b>{datetime.strftime(datetime.today(),'%d %b %Y')}</b>",
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

fig.show()

fig.write_html('today_uv.html')
fig.write_image('today_uv.jpg')

airQuality.graph_forecast()


answer = questionary.confirm("Send message to phone and display analytics?").ask()

if answer == True:
    msg.sendFile('/Users/jonathanrice/Desktop/Pyth/weather/today_uv.jpg')
    sweetviz = sv.analyze(whole_df)
    sweetviz.show_html()
