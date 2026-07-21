"""
weekly_analysis.py
--------------------
The single script the Thursday GitHub Action runs. Replaces the earlier
separate ami_affordability.py / join_vacancy_feasibility.py /
generate_hex_tract_lookup.py — consolidated so there's one file, one job,
one order of operations.

What it does, in order:
  1. Loads rent_history.csv, dedupes to latest listing per property, hex-bins (H3 res 8)
  2. Computes AMI comparison (1-4 person households) for each hex
  3. Geocodes each hex centroid to a census tract GEOID via the free Census
     Geocoder API — only for hexes not already in hex_tract_lookup.csv, so
     this is fast after the first run. (This step needs real internet access,
     which GitHub Actions runners have — it will NOT run in a sandboxed
     analysis environment without that access.)
  4. Joins tract-level USPS vacancy (usps_vacancy_trend_by_tract.csv) and
     housing-demand signals (household_demand_signals_by_tract.csv)
  5. Classifies each hex's development feasibility (4-unit vs. 8-unit
     thresholds, the latter applied in high-vacancy tracts)
  6. Appends one row to ami_affordability_history.csv for this week
  7. Writes el_paso_rent_vs_ami.geojson for the map

Requires: pandas, h3, requests
    pip install pandas h3 requests
"""

import pandas as pd
import h3
import requests
import time
import json
import os

# --- File paths ---
# rent_history.csv stays at the REPO ROOT, since rent_tracker.py fetches into it there.
# Everything specific to this project lives under ami-feasibility/, so this script
# must be run from the repo root (the workflow does this) — that's also why
# RENT_HISTORY_PATH has no folder prefix but the rest do.
RENT_HISTORY_PATH = "rent_history.csv"
VACANCY_PATH = "ami-feasibility/usps_vacancy_trend_by_tract.csv"
DEMAND_PATH = "ami-feasibility/household_demand_signals_by_tract.csv"
HEX_TRACT_CACHE_PATH = "ami-feasibility/hex_tract_lookup.csv"
AFFORDABILITY_HISTORY_PATH = "ami-feasibility/ami_affordability_history.csv"
GEOJSON_OUTPUT_PATH = "ami-feasibility/el_paso_rent_vs_ami.geojson"

RESOLUTION = 8

# --- AMI thresholds — El Paso, TX MSA, FY2025 HUD MFI $72,800 ---
# Update EL_PASO_MFI each spring when HUD publishes new limits
# (huduser.gov/portal/datasets/il.html)
EL_PASO_MFI = 72800
HH_SIZE_FACTORS = {1: 0.70, 2: 0.80, 3: 0.90, 4: 1.00}
AMI = {k: EL_PASO_MFI * v * 0.30 / 12 for k, v in HH_SIZE_FACTORS.items()}

# --- Feasibility thresholds, derived from the proforma sensitivity model ---
# ($/SF/month, market-rate scenario; see README methodology section)
THRESHOLDS_4_UNIT = {"feasible": 1.532, "remodel_feasible": 0.994, "remodel_subsidy_floor": 0.942}
THRESHOLDS_8_UNIT = {"feasible": 1.395, "remodel_feasible": 0.857, "remodel_subsidy_floor": 0.805}

# Data-driven default: top quartile of El Paso tract-level residential
# vacancy. ADJUST if the project settles on a different "high-vacancy"
# definition for the 8-unit conversion assumption.
HIGH_VACANCY_PERCENTILE = 0.75

GEOCODER_URL = "https://geocoding.geo.census.gov/geocoder/geographies/coordinates"


def geocode_tract(lat, lon, retries=3):
    params = {
        "x": lon, "y": lat,
        "benchmark": "Public_AR_Current",
        "vintage": "Current_Current",
        "layers": "Census Tracts",
        "format": "json",
    }
    for attempt in range(retries):
        try:
            r = requests.get(GEOCODER_URL, params=params, timeout=10)
            r.raise_for_status()
            tracts = r.json()["result"]["geographies"].get("Census Tracts", [])
            return tracts[0]["GEOID"] if tracts else None
        except Exception as e:
            if attempt == retries - 1:
                print(f"  Geocoder failed for ({lat:.5f}, {lon:.5f}): {e}")
                return None
            time.sleep(1)


def get_hex_tract_lookup(hex_ids):
    """Geocode each hex centroid, reusing cached results so only new
    hexes (new geographic areas appearing in the listings) get looked up."""
    if os.path.isfile(HEX_TRACT_CACHE_PATH):
        cache = pd.read_csv(HEX_TRACT_CACHE_PATH, dtype={"geoid": str})
    else:
        cache = pd.DataFrame(columns=["hex_id", "geoid"])
    cached_ids = set(cache["hex_id"])

    new_hex_ids = [h for h in hex_ids if h not in cached_ids]
    print(f"{len(hex_ids)} hexes total, {len(new_hex_ids)} new — geocoding those now")

    new_rows = []
    for i, hex_id in enumerate(new_hex_ids):
        lat, lon = h3.cell_to_latlng(hex_id)
        geoid = geocode_tract(lat, lon)
        new_rows.append({"hex_id": hex_id, "geoid": geoid})
        if (i + 1) % 25 == 0:
            print(f"  {i+1}/{len(new_hex_ids)} geocoded")
        time.sleep(0.2)

    if new_rows:
        cache = pd.concat([cache, pd.DataFrame(new_rows)], ignore_index=True)
        cache.to_csv(HEX_TRACT_CACHE_PATH, index=False)

    return cache


def classify_feasibility(rent_per_sf, is_high_vacancy):
    if pd.isna(rent_per_sf):
        return "Insufficient sqft data"
    t = THRESHOLDS_8_UNIT if is_high_vacancy else THRESHOLDS_4_UNIT
    if rent_per_sf >= t["feasible"]:
        return "New construction feasible"
    elif rent_per_sf >= t["remodel_feasible"]:
        return "Conversion feasible, new construction not"
    elif rent_per_sf >= t["remodel_subsidy_floor"]:
        return "Conversion feasible only with subsidy"
    else:
        return "Neither pencils without subsidy"


def main():
    # === 1. Load rent data, dedupe, hex-bin ===
    df = pd.read_csv(RENT_HISTORY_PATH)
    df["capture_date"] = pd.to_datetime(df["capture_date"])
    latest_date = df["capture_date"].max()
    df_all = df.sort_values("capture_date").drop_duplicates(subset="id", keep="last")
    df_all = df_all.dropna(subset=["latitude", "longitude", "price"])
    df_all = df_all[df_all["bedrooms"] <= 6]
    df_all["hex_id"] = df_all.apply(lambda r: h3.latlng_to_cell(r.latitude, r.longitude, RESOLUTION), axis=1)

    sqft_df = df_all.dropna(subset=["squareFootage"])
    sqft_df = sqft_df[sqft_df["squareFootage"] > 0].copy()
    sqft_df["rent_per_sf"] = sqft_df["price"] / sqft_df["squareFootage"]
    sqft_df = sqft_df[(sqft_df["rent_per_sf"] > 0.3) & (sqft_df["rent_per_sf"] < 5)]

    agg = df_all.groupby("hex_id").agg(median_rent=("price", "median"), n_listings=("price", "count")).reset_index()
    sf_agg = sqft_df.groupby("hex_id")["rent_per_sf"].median().reset_index().rename(columns={"rent_per_sf": "median_rent_per_sf"})
    agg = agg.merge(sf_agg, on="hex_id", how="left")

    # === 2. AMI comparison ===
    for hh, thresh in AMI.items():
        agg[f"pct_diff_ami_{hh}p"] = (agg["median_rent"] - thresh) / thresh * 100

    # === 3. Hex -> tract geocoding (cached) ===
    lookup = get_hex_tract_lookup(agg["hex_id"].tolist())
    agg = agg.merge(lookup, on="hex_id", how="left")
    n_unmatched = agg["geoid"].isna().sum()
    if n_unmatched:
        print(f"WARNING: {n_unmatched} of {len(agg)} hexes have no tract match "
              f"(likely just outside El Paso County)")

    # === 4. Vacancy + demand joins ===
    vdf = pd.read_csv(VACANCY_PATH, dtype={"tract": str})
    latest_period = vdf["period"].max()
    vdf_latest = vdf[vdf["period"] == latest_period][["tract", "pct_residential_vacant"]]
    vdf_latest = vdf_latest.rename(columns={"tract": "geoid", "pct_residential_vacant": "vacancy_rate"})
    agg = agg.merge(vdf_latest, on="geoid", how="left")

    high_vacancy_cutoff = vdf_latest["vacancy_rate"].quantile(HIGH_VACANCY_PERCENTILE)
    agg["is_high_vacancy"] = (agg["vacancy_rate"] >= high_vacancy_cutoff).fillna(False)

    ddf = pd.read_csv(DEMAND_PATH, dtype={"tract": str})
    ddf = ddf[["tract", "demand_score", "pct_cost_burdened"]].rename(columns={"tract": "geoid"})
    agg = agg.merge(ddf, on="geoid", how="left")

    # === 5. Feasibility classification ===
    agg["feasibility"] = agg.apply(lambda r: classify_feasibility(r["median_rent_per_sf"], r["is_high_vacancy"]), axis=1)

    print(f"\nVacancy data as of {latest_period}, high-vacancy cutoff: {high_vacancy_cutoff:.1%}")
    print(agg["feasibility"].value_counts())

    # === 6. Weekly history append ===
    row = {
        "week_of": latest_date.strftime("%Y-%m-%d"),
        "n_listings": int(agg["n_listings"].sum()),
        "median_rent": df_all[df_all["capture_date"] == latest_date]["price"].median(),
        "pct_below_ami_4p": round((agg["pct_diff_ami_4p"] < 0).mul(agg["n_listings"]).sum() / agg["n_listings"].sum() * 100, 1),
        "pct_conversion_feasible_only": round(
            agg.loc[agg["feasibility"] == "Conversion feasible, new construction not", "n_listings"].sum()
            / agg["n_listings"].sum() * 100, 1
        ),
        "pct_new_construction_feasible": round(
            agg.loc[agg["feasibility"] == "New construction feasible", "n_listings"].sum()
            / agg["n_listings"].sum() * 100, 1
        ),
    }
    row_df = pd.DataFrame([row])
    if os.path.isfile(AFFORDABILITY_HISTORY_PATH):
        existing = pd.read_csv(AFFORDABILITY_HISTORY_PATH, dtype={"week_of": str})
        if row["week_of"] in existing["week_of"].values:
            print(f"Week {row['week_of']} already in history, skipping append")
        else:
            # pd.concat aligns columns by name and fills NaN for any that
            # don't exist on one side — safer than a raw text append when
            # the schema has grown (e.g. new feasibility columns added
            # after the AMI-only backfill)
            combined = pd.concat([existing, row_df], ignore_index=True)
            combined.to_csv(AFFORDABILITY_HISTORY_PATH, index=False)
            print(f"Appended week {row['week_of']} to {AFFORDABILITY_HISTORY_PATH}")
    else:
        row_df.to_csv(AFFORDABILITY_HISTORY_PATH, index=False)
        print(f"Created {AFFORDABILITY_HISTORY_PATH} with first week's data")

    # === 7. GeoJSON export ===
    features = []
    for _, r in agg.iterrows():
        boundary = h3.cell_to_boundary(r.hex_id)
        coords = [[lon, lat] for lat, lon in boundary]
        coords.append(coords[0])
        props = {
            "hex_id": r.hex_id,
            "median_rent": round(r.median_rent),
            "n_listings": int(r.n_listings),
            "median_rent_per_sf": None if pd.isna(r.median_rent_per_sf) else round(r.median_rent_per_sf, 2),
            "geoid": r.geoid,
            "vacancy_rate": None if pd.isna(r.vacancy_rate) else round(r.vacancy_rate, 4),
            "is_high_vacancy": bool(r.is_high_vacancy),
            "demand_score": None if pd.isna(r.demand_score) else round(r.demand_score, 3),
            "feasibility": r.feasibility,
        }
        for hh in [1, 2, 3, 4]:
            props[f"pct_diff_ami_{hh}p"] = round(r[f"pct_diff_ami_{hh}p"], 1)
            props[f"ami_threshold_{hh}p"] = round(AMI[hh])
        features.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [coords]}, "properties": props})

    with open(GEOJSON_OUTPUT_PATH, "w") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f)
    print(f"\nWrote {len(features)} hexes to {GEOJSON_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
