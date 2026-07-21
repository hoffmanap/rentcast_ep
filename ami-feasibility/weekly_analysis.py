"""
weekly_analysis.py
--------------------
The single script the Thursday GitHub Action runs.

What it does, in order:
  1. Loads rent_history.csv, reconstructs the point-in-time active-listing
     snapshot as of the latest capture_date, hex-bins it (H3 res 8)
  2. Computes AMI comparison (1-4 person households) for each hex
  3. Geocodes each hex centroid to a census tract GEOID via the free Census
     Geocoder API — only for hexes not already in hex_tract_lookup.csv
  4. Joins tract-level USPS vacancy and housing-demand signals
  5. Classifies each hex's development feasibility (4-unit vs. 8-unit
     thresholds, the latter applied in high-vacancy tracts)
  6. Appends/updates one row in ami_affordability_history.csv for this week
  7. Writes el_paso_rent_vs_ami.geojson for the map

compute_snapshot() is factored out so the exact same logic can be reused by
backfill_history.py to rebuild every historical week consistently — see
that script for why: the previous version computed "this week's" stats
from an all-time cumulative dedup regardless of which week triggered the
run, which meant every week's feasibility numbers actually reflected
today's full listing history, not that week's point-in-time market. That
also made backfilling historical weeks on the same basis impossible
without this refactor.

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
RENT_HISTORY_PATH = "rent_history.csv"
VACANCY_PATH = "ami-feasibility/usps_vacancy_trend_by_tract.csv"
DEMAND_PATH = "ami-feasibility/household_demand_signals_by_tract.csv"
HEX_TRACT_CACHE_PATH = "ami-feasibility/hex_tract_lookup.csv"
AFFORDABILITY_HISTORY_PATH = "ami-feasibility/ami_affordability_history.csv"
GEOJSON_OUTPUT_PATH = "ami-feasibility/el_paso_rent_vs_ami.geojson"

RESOLUTION = 8

EL_PASO_MFI = 72800
HH_SIZE_FACTORS = {1: 0.70, 2: 0.80, 3: 0.90, 4: 1.00}
AMI = {k: EL_PASO_MFI * v * 0.30 / 12 for k, v in HH_SIZE_FACTORS.items()}

THRESHOLDS_4_UNIT = {"feasible": 1.532, "remodel_feasible": 0.994, "remodel_subsidy_floor": 0.942}
THRESHOLDS_8_UNIT = {"feasible": 1.395, "remodel_feasible": 0.857, "remodel_subsidy_floor": 0.805}

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
    """Geocode each hex centroid, reusing cached results. The hex→tract
    mapping is purely geographic and never changes week to week, which is
    exactly why the same cache works for backfilling historical weeks too."""
    if os.path.isfile(HEX_TRACT_CACHE_PATH):
        cache = pd.read_csv(HEX_TRACT_CACHE_PATH, dtype={"geoid": str})
    else:
        cache = pd.DataFrame(columns=["hex_id", "geoid"])
    cached_ids = set(cache["hex_id"])

    new_hex_ids = [h for h in hex_ids if h not in cached_ids]
    if new_hex_ids:
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


def build_point_in_time_snapshot(raw_df, as_of_date):
    """What was active AS OF a given week: for each property, take its most
    recent capture on or before as_of_date, ignoring anything captured
    later. This is the single source of truth for every stat computed for
    that week — n_listings, median rent, AMI comparison, feasibility, and
    property-type breakdown all use this same snapshot now, rather than the
    old split where feasibility used an all-time cumulative dedup but
    median_rent/property-type used just that week's raw fetch batch."""
    snap = raw_df[raw_df["capture_date"] <= as_of_date]
    snap = snap.sort_values("capture_date").drop_duplicates(subset="id", keep="last")
    snap = snap.dropna(subset=["latitude", "longitude", "price"])
    snap = snap[snap["bedrooms"] <= 6]
    return snap


def compute_property_type_stats(snapshot):
    """Single-family AMI check and new-vs-existing construction rent
    comparison. Returns None if propertyType/listingType don't exist yet or
    have no real values in this snapshot — true for any week before
    rent_tracker.py started capturing them."""
    if "propertyType" not in snapshot.columns or snapshot["propertyType"].isna().all():
        return None

    sfr = snapshot[snapshot["propertyType"] == "Single Family"]
    if len(sfr) < 10:
        return None

    stats = {
        "n_single_family": len(sfr),
        "median_rent_single_family": sfr["price"].median(),
        "pct_below_ami_4p_single_family": round((sfr["price"] < AMI[4]).mean() * 100, 1),
    }

    if "listingType" in snapshot.columns and not snapshot["listingType"].isna().all():
        new_constr = snapshot[snapshot["listingType"] == "New Construction"]
        existing = snapshot[snapshot["listingType"] != "New Construction"]
        if len(new_constr) >= 5:
            stats["n_new_construction"] = len(new_constr)
            stats["median_rent_new_construction"] = new_constr["price"].median()
            stats["median_rent_existing_stock"] = existing["price"].median()

    return stats


def compute_snapshot(snapshot, as_of_date, hex_tract_lookup, vacancy_df, demand_df, build_geojson=False):
    """The full pipeline for one point-in-time snapshot: hex-bin, AMI
    comparison, tract/vacancy/demand join, feasibility classification,
    property-type stats. Returns (row_dict, geojson_dict_or_None).
    Shared by both the live weekly run and the historical backfill so every
    week is computed identically."""
    snap = snapshot.copy()
    snap["hex_id"] = snap.apply(lambda r: h3.latlng_to_cell(r.latitude, r.longitude, RESOLUTION), axis=1)

    sqft_df = snap.dropna(subset=["squareFootage"])
    sqft_df = sqft_df[sqft_df["squareFootage"] > 0].copy()
    sqft_df["rent_per_sf"] = sqft_df["price"] / sqft_df["squareFootage"]
    sqft_df = sqft_df[(sqft_df["rent_per_sf"] > 0.3) & (sqft_df["rent_per_sf"] < 5)]

    agg = snap.groupby("hex_id").agg(median_rent=("price", "median"), n_listings=("price", "count")).reset_index()
    sf_agg = sqft_df.groupby("hex_id")["rent_per_sf"].median().reset_index().rename(columns={"rent_per_sf": "median_rent_per_sf"})
    agg = agg.merge(sf_agg, on="hex_id", how="left")

    for hh, thresh in AMI.items():
        agg[f"pct_diff_ami_{hh}p"] = (agg["median_rent"] - thresh) / thresh * 100

    agg = agg.merge(hex_tract_lookup, on="hex_id", how="left")

    latest_period = vacancy_df["period"].max()
    vdf_latest = vacancy_df[vacancy_df["period"] == latest_period][["tract", "pct_residential_vacant"]]
    vdf_latest = vdf_latest.rename(columns={"tract": "geoid", "pct_residential_vacant": "vacancy_rate"})
    agg = agg.merge(vdf_latest, on="geoid", how="left")

    high_vacancy_cutoff = vdf_latest["vacancy_rate"].quantile(HIGH_VACANCY_PERCENTILE)
    agg["is_high_vacancy"] = (agg["vacancy_rate"] >= high_vacancy_cutoff).fillna(False)

    ddf = demand_df[["tract", "demand_score", "pct_cost_burdened"]].rename(columns={"tract": "geoid"})
    agg = agg.merge(ddf, on="geoid", how="left")

    agg["feasibility"] = agg.apply(lambda r: classify_feasibility(r["median_rent_per_sf"], r["is_high_vacancy"]), axis=1)

    sfr_stats = compute_property_type_stats(snap)

    row = {
        "week_of": as_of_date.strftime("%Y-%m-%d"),
        "n_listings": int(agg["n_listings"].sum()),
        "median_rent": snap["price"].median(),
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
    if sfr_stats:
        row.update(sfr_stats)

    geojson_dict = None
    if build_geojson:
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
        geojson_dict = {"type": "FeatureCollection", "features": features}

    return row, geojson_dict


def upsert_week_row(row):
    row_df = pd.DataFrame([row])
    if os.path.isfile(AFFORDABILITY_HISTORY_PATH):
        existing = pd.read_csv(AFFORDABILITY_HISTORY_PATH, dtype={"week_of": str})
        if row["week_of"] in existing["week_of"].values:
            existing = existing[existing["week_of"] != row["week_of"]]
            print(f"Replacing existing row for week {row['week_of']} with fresh computation")
        combined = pd.concat([existing, row_df], ignore_index=True).sort_values("week_of")
        combined.to_csv(AFFORDABILITY_HISTORY_PATH, index=False)
        print(f"{AFFORDABILITY_HISTORY_PATH} now has {len(combined)} weeks")
    else:
        row_df.to_csv(AFFORDABILITY_HISTORY_PATH, index=False)
        print(f"Created {AFFORDABILITY_HISTORY_PATH} with first week's data")


def main():
    df = pd.read_csv(RENT_HISTORY_PATH)
    df["capture_date"] = pd.to_datetime(df["capture_date"])
    latest_date = df["capture_date"].max()

    snapshot = build_point_in_time_snapshot(df, latest_date)
    snapshot_hex_ids = snapshot.apply(lambda r: h3.latlng_to_cell(r.latitude, r.longitude, RESOLUTION), axis=1).tolist()
    hex_tract_lookup = get_hex_tract_lookup(sorted(set(snapshot_hex_ids)))

    vacancy_df = pd.read_csv(VACANCY_PATH, dtype={"tract": str})
    demand_df = pd.read_csv(DEMAND_PATH, dtype={"tract": str})

    row, geojson_dict = compute_snapshot(snapshot, latest_date, hex_tract_lookup, vacancy_df, demand_df, build_geojson=True)

    print(f"\nWeek of {row['week_of']}: {row['n_listings']} listings, "
          f"{row['pct_below_ami_4p']}% below 4p AMI, "
          f"{row['pct_conversion_feasible_only']}% conversion-feasible only, "
          f"{row['pct_new_construction_feasible']}% new-construction feasible")
    if "n_single_family" in row:
        print(f"Single-family: n={row['n_single_family']}, median rent ${row['median_rent_single_family']:.0f}, "
              f"{row['pct_below_ami_4p_single_family']}% below 4p AMI")

    upsert_week_row(row)

    with open(GEOJSON_OUTPUT_PATH, "w") as f:
        json.dump(geojson_dict, f)
    print(f"Wrote {len(geojson_dict['features'])} hexes to {GEOJSON_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
