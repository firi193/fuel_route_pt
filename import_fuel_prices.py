import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fuel_route_project.settings")
django.setup()
import csv
from fuel_api.models import FuelPrice

def run():
    with open('data/fuel-prices-preprocessed.csv', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            FuelPrice.objects.create(
                opis_id=row['OPIS Truckstop ID'],
                truckstop_name=row['Truckstop Name'],
                address=row['Address'],
                city=row['City'],
                state=row['State'],
                rack_id=row['Rack ID'],
                retail_price=float(row['Retail Price']),
                lat=float(row['lat']),
                lon=float(row['lon']),
            )


if __name__ == "__main__":
    run()