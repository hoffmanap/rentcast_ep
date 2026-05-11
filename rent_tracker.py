import requests
import pandas as pd
import os
from datetime import datetime

def fetch_rentals():
    api_key = os.getenv("RENTCAST_API_KEY")
    url = "https://api.rentcast.io/v1/listings/rental/long-term"
    
    # Parameters for El Paso with the 500 listing limit
    querystring = {
        "city": "El Paso",
        "state": "TX",
        "status": "Active",
        "limit": 500 
    }

    headers = {
        "accept": "application/json",
        "X-Api-Key": api_key
    }

    try:
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        listings = response.json()

        # Convert JSON to DataFrame
        df = pd.DataFrame(listings)

        # Add a capture date for historical tracking
        df['capture_date'] = datetime.now().strftime('%Y-%m-%d')

        # Define the specific fields you requested + core rental data
        cols_to_keep = [
            'id', 
            'formattedAddress', 
            'zipCode',      # Zip Code
            'price', 
            'bedrooms', 
            'bathrooms', 
            'squareFootage', 
            'yearBuilt',    # Year Built
            'latitude',     # Latitude
            'longitude',    # Longitude
            'propertyType', 
            'capture_date'
        ]
        
        # Ensure only available columns are selected (prevents errors if a field is missing)
        df = df[[c for c in cols_to_keep if c in df.columns]]

        # Append to the local CSV file
        file_path = 'rent_history.csv'
        if not os.path.isfile(file_path):
            df.to_csv(file_path, index=False)
        else:
            df.to_csv(file_path, mode='a', header=False, index=False)

        print(f"Successfully logged {len(df)} rental listings for El Paso.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fetch_rentals()
