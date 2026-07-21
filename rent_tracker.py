import requests
import pandas as pd
import os
from datetime import datetime

RENT_HISTORY_PATH = "rent_history.csv"
PRICE_HISTORY_PATH = "rent_price_history.csv"


def fetch_and_append_rentals():
    api_key = os.getenv("RENTCAST_API_KEY")
    if not api_key:
        print("Error: RENTCAST_API_KEY not found in environment variables.")
        return

    url = "https://api.rentcast.io/v1/listings/rental/long-term"
    querystring = {"city": "El Paso", "state": "TX", "status": "Active", "limit": 500}
    headers = {"accept": "application/json", "X-Api-Key": api_key}

    try:
        print("Fetching up to 500 listings for El Paso...")
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        listings = response.json()
        capture_date = datetime.now().strftime('%Y-%m-%d')

        # ------------------------------------------------------------------
        # 1. Main weekly snapshot — one row per active listing per week.
        # json_normalize (not plain DataFrame) so nested fields like
        # hoa.fee flatten into hoa_fee instead of staying as dict objects.
        # ------------------------------------------------------------------
        df = pd.json_normalize(listings, sep='_')
        df['capture_date'] = capture_date

        cols = [
            'capture_date', 'id', 'formattedAddress', 'zipCode', 'county',
            'price', 'bedrooms', 'bathrooms', 'squareFootage', 'lotSize', 'yearBuilt',
            'propertyType', 'status', 'listingType', 'hoa_fee',
            'daysOnMarket', 'listedDate', 'removedDate', 'createdDate', 'lastSeenDate',
            'mlsName', 'mlsNumber',
            'latitude', 'longitude',
        ]
        df = df[[c for c in cols if c in df.columns]]

        write_with_schema_check(df, RENT_HISTORY_PATH, dedupe_cols=None)

        # ------------------------------------------------------------------
        # 2. Price history — RentCast's own retroactive per-property history,
        # flattened to one row per (property id, history date). This is
        # cumulative on their end, so we dedupe against what's already
        # recorded rather than re-appending the same past entries every week.
        # ------------------------------------------------------------------
        history_rows = []
        for listing in listings:
            prop_id = listing.get('id')
            history = listing.get('history') or {}
            for hist_date, entry in history.items():
                history_rows.append({
                    'id': prop_id,
                    'history_date': hist_date,
                    'event': entry.get('event'),
                    'price': entry.get('price'),
                    'listingType': entry.get('listingType'),
                    'listedDate': entry.get('listedDate'),
                    'removedDate': entry.get('removedDate'),
                    'daysOnMarket': entry.get('daysOnMarket'),
                    'first_seen_capture_date': capture_date,
                })

        if history_rows:
            hist_df = pd.DataFrame(history_rows)
            write_with_schema_check(hist_df, PRICE_HISTORY_PATH, dedupe_cols=['id', 'history_date'])
        else:
            print("No history entries returned this week")

    except Exception as e:
        print(f"An error occurred during execution: {e}")


def write_with_schema_check(new_df, file_path, dedupe_cols=None):
    """Append new_df to file_path. If the file doesn't exist yet, create it.
    If it exists but has a different (e.g. older, narrower) column set,
    reconcile via pd.concat instead of a raw text append — a blind
    mode='a' append would silently misalign columns whenever the schema
    has grown, which is exactly what happened going from the old 11-column
    rent_history.csv to this expanded version."""
    if not os.path.isfile(file_path):
        new_df.to_csv(file_path, index=False)
        print(f"Created new file: {file_path} with {len(new_df)} rows")
        return

    existing = pd.read_csv(file_path, dtype=str)
    same_schema = list(existing.columns) == list(new_df.columns)

    if dedupe_cols:
        # e.g. price history: only keep rows not already recorded
        existing_keys = existing.set_index(dedupe_cols).index
        new_df = new_df[~new_df.set_index(dedupe_cols).index.isin(existing_keys)]
        if new_df.empty:
            print(f"No new rows for {file_path} this week")
            return

    if same_schema:
        new_df.to_csv(file_path, mode='a', header=False, index=False)
        print(f"Appended {len(new_df)} new rows to {file_path}")
    else:
        # Column set changed (e.g. this week's script upgrade) — align by
        # name via concat rather than a positional text append, so old rows
        # just get NaN in the new columns instead of corrupted data.
        combined = pd.concat([existing, new_df], ignore_index=True)
        combined.to_csv(file_path, index=False)
        print(f"Schema changed — reconciled and rewrote {file_path} "
              f"({len(existing)} existing + {len(new_df)} new = {len(combined)} rows)")


if __name__ == "__main__":
    fetch_and_append_rentals()
