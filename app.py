from flask import Flask, request, render_template
import pandas as pd
import numpy as np
from sklearn.neighbors import BallTree
import re
import logging


logging.basicConfig(filename='flask_error.log', level=logging.DEBUG)

app = Flask(__name__)

#Load and prepare dataset
cities = pd.read_csv("cities_over_10000.csv")
cities[['lat', 'lon']] = cities['Coordinates'].str.extract(r'([\-\d.]+)[,\s]+([\-\d.]+)').astype(float)
cities = cities.dropna(subset=['lat', 'lon'])
coords_rad = np.radians(cities[['lat', 'lon']].values)
tree = BallTree(coords_rad, metric='haversine')



def split_by_comma(s):
    return re.split(r',\s*', s)

def contains_letter(s):
    return any(char.isalpha() for char in s)

def remove_letter(s, letter):
    return s.replace(letter.lower(), '').replace(letter.upper(), '')


def convert_to_dec(coord_str):
    # Accepts both "31.872 N, 122.273 E" and "37.872, -122.273"
    match = re.findall(r'([-\d.]+)\s*([NSEW]?)', coord_str.upper())

    if len(match) < 2:
        raise ValueError("Could not parse coordinates. Use format like '31.872 N, 122.273 E'. Make sure to delimit with a comma.")

    lat_val, lat_dir = match[0]
    lon_val, lon_dir = match[1]

    lat = float(lat_val)
    lon = float(lon_val)

    if lat_dir == "S":
        lat = -abs(lat)
    elif lat_dir == "N":
        lat = abs(lat)

    if lon_dir == "W":
        lon = -abs(lon)
    elif lon_dir == "E":
        lon = abs(lon)

    return lat, lon


def antipode_func(string):

    home_coords = convert_to_dec(string)

    home_lat = home_coords[0]
    home_long = home_coords[1]

    antipode_lat = -home_lat
    
    if home_long >= 0:
        antipode_long = home_long - 180
    else:
        antipode_long = home_long + 180
    
    #print(f"Input coordinates: {home_coords}, Antipode coordinates: {antipode_lat, antipode_long}")
    return antipode_lat, antipode_long

def find_nearest_city(lat, lon):
    query_rad = np.radians([[lat, lon]])
    dist, idx = tree.query(query_rad, k=1)

    distance_km = float(dist[0][0] * 6371.0)  # Explicit float conversion

    row = cities.iloc[idx[0][0]]

    return {
        'Nearest City': str(row['Name']),
        'Country': str(row['Country name EN']),
        'Latitude': float(row['lat']),
        'Longitude': float(row['lon']),
        'Distance from antipode (km)': round(distance_km, 2)
    }

def final(string):
    input_coords = string
    antipode_coords = antipode_func(string)

    input_closest_city = find_nearest_city(convert_to_dec(string)[0], convert_to_dec(string)[1])
    
    query_rad = np.radians([[antipode_coords[0], antipode_coords[1]]])
    dist, idx = tree.query(query_rad, k=1)

    distance_km = float(dist[0][0] * 6371.0)  # Explicit float conversion

    row = cities.iloc[idx[0][0]]

    result = (
        f"The closest city to ({string}) is {input_closest_city['Nearest City']}, and the antipode of your input coordinates is {antipode_coords}.\n"
        f"The nearest city to the antipode is {row['Name']} in {row['Country name EN']}.\n"
        f"The coordinates of {row['Name']} are {row['lat']:.5f}, {row['lon']:.5f} and it is {distance_km:.2f} km from the antipode of your input coordinates."
        
        #f"Nearest city: {row['Name']}, {row['Country name EN']}\n"
        #f"Latitude: {row['lat']:.5f}, Longitude: {row['lon']:.5f}\n"
        #f"Distance: {distance_km:.2f} km"
    )

    return result

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST":
        coords = request.form["coords"]
        try:
            # Get antipode coords
            anti_lat, anti_lon = antipode_func(coords)
            
            # Nearest city to antipode
            antipode_city = find_nearest_city(anti_lat, anti_lon)
            antipode_city["Antipode"] = f"{anti_lat:.5f}, {anti_lon:.5f}"
            
            # Nearest city to input coords
            input_lat, input_lon = convert_to_dec(coords)
            input_city = find_nearest_city(input_lat, input_lon)
            
            # Prepare final result dictionary combining both
            result = {
                # Input coordinates as entered by user (string)
                "InputCoordinates": coords.strip(),
                
                # Nearest city to input
                "NearestCityInput": input_city['Nearest City'],
                "InputCountry": input_city["Country"],
                
                # Nearest city to antipode info (rename distance key to 'Distance')
                "Nearest City": antipode_city["Nearest City"],
                "Country": antipode_city["Country"],
                "Latitude": antipode_city["Latitude"],
                "Longitude": antipode_city["Longitude"],
                "Distance": antipode_city["Distance from antipode (km)"],
                
                "Population": antipode_city.get("Population", None),
                # Antipode coordinates string
                "Antipode": antipode_city["Antipode"]
            }
            
        except Exception as e:
            result = {"error": str(e)}
    return render_template("index.html", result=result)



if __name__ == "__main__":
    app.run(debug=True)


