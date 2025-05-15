import pandas as pd
from geopy.geocoders import Nominatim
import time
import os

INPUT_CSV = 'data/fuel-prices-for-be-assessment.csv'
OUTPUT_CSV = 'data/fuel-prices-preprocessed.csv'

geolocator = Nominatim(user_agent="fuel_data_preprocessor")

def geocode(row):
    address = f"{row['Address']}, {row['City']}, {row['State']}"
    try:
        location = geolocator.geocode(address)
        if location:
            return pd.Series([location.latitude, location.longitude])
    except:
        pass
    return pd.Series([None, None])

def preprocess():
    # Load input data
    df_input = pd.read_csv(INPUT_CSV)

    # Check if output file already exists to resume from
    if os.path.exists(OUTPUT_CSV):
        df_done = pd.read_csv(OUTPUT_CSV)
        done_addresses = set(df_done['Address'] + df_done['City'] + df_done['State'])
        print(f"Resuming from previous progress: {len(df_done)} rows already done.")
    else:
        df_done = pd.DataFrame()
        done_addresses = set()

    rows = []
    for i, row in df_input.iterrows():
        addr_key = row['Address'] + row['City'] + row['State']
        if addr_key in done_addresses:
            continue

        lat, lon = geocode(row)
        if lat is not None and lon is not None:
            row['lat'] = lat
            row['lon'] = lon
            rows.append(row)

        # Save every 10 rows to prevent progress loss
        if len(rows) >= 10:
            df_partial = pd.DataFrame(rows)
            df_done = pd.concat([df_done, df_partial], ignore_index=True)
            df_done.to_csv(OUTPUT_CSV, index=False)
            rows = []
            print(f"Saved {len(df_done)} rows so far.")
            time.sleep(1)  # obey Nominatim's rate limit

    # Final save
    if rows:
        df_partial = pd.DataFrame(rows)
        df_done = pd.concat([df_done, df_partial], ignore_index=True)
        df_done.to_csv(OUTPUT_CSV, index=False)
        print(f"Final save: {len(df_done)} rows total.")

if __name__ == '__main__':
    preprocess()
