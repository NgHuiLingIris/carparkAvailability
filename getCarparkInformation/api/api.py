import flask
import requests
import json
import pandas as pd
import numpy as np
from pandas.io.json import json_normalize
from geopandas import GeoDataFrame
from shapely.geometry import Point
from shapely.ops import nearest_points
import matplotlib.pyplot as plt
from flask import request, jsonify

app = flask.Flask(__name__)
app.config["DEBUG"] = True

#Prepare data
url = 'https://api.data.gov.sg/v1/transport/carpark-availability'
response = requests.get(url)
data = response.json()
df = json_normalize(data['items'][0]['carpark_data'])
cpInfo_df = pd.DataFrame(columns = ['carpark_number','update_datetime','lot_type','lots_available','total_lots'])
carparkAvailability = pd.DataFrame(columns = ['carpark_number','update_datetime','lot_type','lots_available','total_lots'])

for i in range(len(df)):
    cpInfo_df = json_normalize(df['carpark_info'][i])
    cpInfo_df['carpark_number'] = df['carpark_number'][i]
    cpInfo_df['update_datetime'] = df['update_datetime'][i]
    carparkAvailability = carparkAvailability.append(cpInfo_df, sort = True, ignore_index = False)

dfCarparkInformation = pd.read_csv("hdb-carpark-information.csv") 


@app.route('/', methods=['GET'])
def home():
    return '''<h1>Carpark Availability</h1>'''


@app.route('/api/v1/resources/availableCarparks', methods=['GET'])
def getCarparkAvailability():
    #carparkNumberIndex = 'TB1'
    if 'carparkNumberIndex' in request.args:
        carparkNumberIndex = str(request.args['carparkNumberIndex'])
    else:
        return "Error: No carparkNumberIndex field provided. Please specify a carparkNumberIndex."
    print(carparkNumberIndex)
    myXCoord = dfCarparkInformation.loc[dfCarparkInformation['car_park_no'] == carparkNumberIndex].x_coord
    myYCoord = dfCarparkInformation.loc[dfCarparkInformation['car_park_no'] == carparkNumberIndex].y_coord
    geometry = [Point(xy) for xy in zip(dfCarparkInformation.x_coord, dfCarparkInformation.y_coord)]
    geoDfCarparkInformation = dfCarparkInformation.drop(['x_coord', 'y_coord'], axis=1).copy()
    crs = {'init': 'epsg:4326'}
    geoDfCarparkInformation = GeoDataFrame(geoDfCarparkInformation, crs=crs, geometry=geometry)
    geoDfCarparkInformation['distance'] = geoDfCarparkInformation['geometry'].distance(Point(myXCoord,myYCoord))
    nearestCarpark = geoDfCarparkInformation.sort_values(by=['distance'])[0:6].copy()
    carparkInformationAndAvailability = carparkAvailability.merge(nearestCarpark, left_on='carpark_number', right_on='car_park_no')
    carparkAvailabilityCleaned = carparkInformationAndAvailability.copy()
    carparkAvailabilityCleaned = carparkAvailabilityCleaned.drop(['carpark_number'],axis=1).drop(['update_datetime'],axis=1).drop(['car_park_no'],axis=1).drop(['type_of_parking_system'],axis=1).drop(['night_parking'],axis=1).drop(['car_park_decks'],axis=1).drop(['gantry_height'],axis=1).drop(['car_park_basement'],axis=1).drop(['geometry'],axis=1).drop(['distance'],axis=1).drop('short_term_parking',axis=1).drop('total_lots',axis=1)
    carparkAvailabilityCleaned = carparkAvailabilityCleaned[carparkAvailabilityCleaned.lots_available != '0']
    carparkAvailabilityResultTotal = carparkAvailabilityCleaned.groupby(['address'])['lots_available'].sum()
    return carparkAvailabilityResultTotal.to_json()

app.run()