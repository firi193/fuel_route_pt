import openrouteservice
from openrouteservice import convert
import pandas as pd
import folium
from geopy.geocoders import Nominatim
import os
from pathlib import Path
from geopy.distance import geodesic
from fuel_api.models import FuelPrice
import math
import uuid


API_KEY = os.getenv('ORS_API_KEY')
if not API_KEY:
    raise ValueError("OpenRouteService API key not found. Set the ORS_API_KEY environment variable.")

client = openrouteservice.Client(key=API_KEY)
BASE_DIR = Path(__file__).resolve().parent.parent

geolocator = Nominatim(user_agent="fuel_locator", timeout=10)

def geocode(location):
    loc = geolocator.geocode(location)
    return [loc.longitude, loc.latitude]

def get_distance(coord1, coord2):
    return geodesic(coord1[::-1], coord2[::-1]).miles  # ORS gives (lon, lat); geodesic wants (lat, lon)

def get_prices_queryset_as_df():
    qs = FuelPrice.objects.all().values(
        'opis_id', 'truckstop_name', 'address', 'city', 'state', 'rack_id', 'retail_price', 'lat', 'lon'
    )
    df = pd.DataFrame.from_records(qs)
    df.columns = df.columns.str.strip()  # Strip spaces once here
    return df

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)) * 0.621371  # km → miles

def get_nearest_fuel_stop_from_db(lat, lon, radius_miles=50):
    lat_range = radius_miles / 69
    lon_range = radius_miles / 54

    nearby_stops = FuelPrice.objects.filter(
        lat__isnull=False,
        lon__isnull=False,
        lat__range=(lat - lat_range, lat + lat_range),
        lon__range=(lon - lon_range, lon + lon_range)
    ).values('lat', 'lon', 'retail_price')

    if not nearby_stops.exists():
        return None

    nearest = min(
        nearby_stops,
        key=lambda row: haversine(lat, lon, row['lat'], row['lon'])
    )
    return nearest


def get_route_with_stops(start_loc, end_loc):
    start_coord = geocode(start_loc)
    end_coord = geocode(end_loc)

    route = client.directions(
        coordinates=[start_coord, end_coord],
        profile='driving-car',
        format='geojson'
    )

    coords = route['features'][0]['geometry']['coordinates']
    total_distance = 0
    last_fuel = 0
    fuel_stops = []

    prices = get_prices_queryset_as_df()
    prices['retail_price'] = pd.to_numeric(prices['retail_price'], errors='coerce')

    for i in range(1, len(coords)):
        segment = get_distance(coords[i-1], coords[i])
        total_distance += segment

        if total_distance - last_fuel >= 500:
            mid = coords[i]
            stop = get_nearest_fuel_stop_from_db(mid[1], mid[0])
            if stop is None:
                continue

            fuel_stops.append({
                'lat': stop['lat'],
                'lon': stop['lon'],
                'price': stop['retail_price'],
                'stop_mile': round(total_distance, 2)
            })
            last_fuel = total_distance

    gallons = total_distance / 10  # 10 mpg
    avg_price = (
        sum([stop['price'] for stop in fuel_stops]) / len(fuel_stops)
        if fuel_stops else prices['retail_price'].mean()
    )
    total_cost = round(gallons * avg_price, 2)

    # Create unique map file
    map_id = str(uuid.uuid4())[:8]
    map_path = f'fuel_api/static/route_map_{map_id}.html'
    m = folium.Map(location=[start_coord[1], start_coord[0]], zoom_start=5)
    folium.PolyLine([(lat, lon) for lon, lat in coords], color='blue').add_to(m)
    for stop in fuel_stops:
        folium.Marker([stop['lat'], stop['lon']], popup=f"${stop['price']}").add_to(m)
    m.save(map_path)

    return {
        "total_miles": round(total_distance, 2),
        "fuel_stops": fuel_stops,
        "total_cost_usd": total_cost,
        "map_url": f"/static/route_map_{map_id}.html"
    }