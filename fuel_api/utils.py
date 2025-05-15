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
from decouple import config


API_KEY = config('ORS_API_KEY')
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


def get_route_with_stops(start_loc, end_loc, request):
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
    last_price = None
    fuel_stops = []

    for i in range(1, len(coords)):
        segment = get_distance(coords[i - 1], coords[i])
        total_distance += segment

        if total_distance - last_fuel >= 500:
            mid = coords[i]
            stop = get_nearest_fuel_stop_from_db(mid[1], mid[0])
            if stop is None:
                continue

            segment_miles = total_distance - last_fuel
            gallons = segment_miles / 10  # 10 mpg
            segment_cost = gallons * stop['retail_price']

            fuel_stops.append({
                'lat': stop['lat'],
                'lon': stop['lon'],
                'stop_mile': round(total_distance, 2),
                'price_per_gallon': round(stop['retail_price'], 3),
                'segment_miles': round(segment_miles, 2),
                'gallons': round(gallons, 2),
                'segment_cost_usd': round(segment_cost, 2)
            })

            last_fuel = total_distance
            last_price = stop['retail_price']

    # Handle final segment to destination if any
    final_segment = total_distance - last_fuel
    if final_segment > 0 and last_price:
        final_gallons = final_segment / 10
        final_cost = final_gallons * last_price

        fuel_stops.append({
            'lat': end_coord[1],
            'lon': end_coord[0],
            'stop_mile': round(total_distance, 2),
            'price_per_gallon': round(last_price, 3),
            'segment_miles': round(final_segment, 2),
            'gallons': round(final_gallons, 2),
            'segment_cost_usd': round(final_cost, 2),
            'note': 'final segment'
        })

    total_cost = round(sum(stop['segment_cost_usd'] for stop in fuel_stops), 2)

    # Create map
    map_id = str(uuid.uuid4())[:8]
    map_path = f'fuel_api/static/route_map_{map_id}.html'
    m = folium.Map(location=[start_coord[1], start_coord[0]], zoom_start=5)
    folium.PolyLine([(lat, lon) for lon, lat in coords], color='blue').add_to(m)
    for stop in fuel_stops:
        folium.Marker([stop['lat'], stop['lon']],
                      popup=f"${stop['price_per_gallon']}").add_to(m)
    m.save(map_path)

    host_prefix = f"{request.scheme}://{request.get_host()}"

    return {
        "total_miles": round(total_distance, 2),
        "fuel_stops": fuel_stops,
        "total_cost_usd": total_cost,
        "map_url": f"{host_prefix}/static/route_map_{map_id}.html"
    }
