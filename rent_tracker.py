import requests
import pandas as pd
import os
from datetime import datetime

def fetch_rentals():
    api_key = os.getenv("RENTCAST_API_KEY")
    # Endpoint for active long-term rental listings
    url = "https://api.rentcast.io/v1/listings/rental/long-term"
    
    # Parameters for El Paso
    querystring = {
        "city": "El Paso",
        "state": "TX",
        "status": "Active",
        "limit": 50  # Adjust based on how many listings you want per week
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

        # Add metadata for tracking
        df['capture_date'] = datetime.now().strftime('%Y-%m-%d')

        # Select columns relevant to your analysis
        # RentCast provides rich data like 'propertyType', 'sqft', 'daysOnMarket'
        cols_to_keep = ['id', 'formattedAddress', 'price', 'bedrooms', 'bathrooms', 'squareFootage', 'propertyType', 'capture_date']
        df = df[cols_to_keep]

        # Append to your local CSV
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