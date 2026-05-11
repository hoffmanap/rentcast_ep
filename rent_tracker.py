import requests
import pandas as pd
import os
from datetime import datetime

def fetch_and_append_rentals():
    # Retrieve the API Key from your GitHub Secrets
    api_key = os.getenv("RENTCAST_API_KEY")
    
    if not api_key:
        print("Error: RENTCAST_API_KEY not found in environment variables.")
        return

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
        print(f"Fetching up to 500 listings for El Paso...")
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        listings = response.json()

        # Convert the JSON response into a flat table (DataFrame)
        df = pd.DataFrame(listings)
        
        # Add a timestamp to distinguish this week's data from others
        df['capture_date'] = datetime.now().strftime('%Y-%m-%d')

        # Select and organize the specific columns you requested
        cols = [
            'capture_date', 
            'id', 
            'formattedAddress', 
            'zipCode', 
            'price', 
            'bedrooms', 
            'bathrooms', 
            'squareFootage', 
            'yearBuilt', 
            'latitude', 
            'longitude'
        ]
        
        # Filter to ensure we only include existing columns to avoid errors
        df = df[[c for c in cols if c in df.columns]]

        file_path = 'rent_history.csv'

        # PERSISTENCE LOGIC:
        # If the file doesn't exist, create it with headers.
        # If it does exist, append new data without adding the header row again.
        if not os.path.isfile(file_path):
            df.to_csv(file_path, index=False)
            print(f"Created new file: {file_path}")
        else:
            df.to_csv(file_path, mode='a', header=False, index=False)
            print(f"Successfully appended {len(df)} new rows to {file_path}")

    except Exception as e:
        print(f"An error occurred during execution: {e}")

if __name__ == "__main__":
    fetch_and_append_rentals()
