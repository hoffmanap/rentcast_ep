"""
backfill_history.py
----------------------
Run this ONCE to rebuild ami_affordability_history.csv from scratch,
computing every historical week with the exact same point-in-time logic
weekly_analysis.py uses for the live week. Needs no new geocoding — reuses
the existing hex_tract_lookup.csv, since a hex's census tract never changes.

Usage: python backfill_history.py
(Run from the repo root, same as weekly_analysis.py)
"""

import pandas as pd
from weekly_analysis import (
    RENT_HISTORY_PATH, VACANCY_PATH, DEMAND_PATH, HEX_TRACT_CACHE_PATH,
    AFFORDABILITY_HISTORY_PATH,
    build_point_in_time_snapshot, compute_snapshot, get_hex_tract_lookup,
)


def main():
    df = pd.read_csv(RENT_HISTORY_PATH)
    df["capture_date"] = pd.to_datetime(df["capture_date"])
    all_weeks = sorted(df["capture_date"].unique())

    vacancy_df = pd.read_csv(VACANCY_PATH, dtype={"tract": str})
    demand_df = pd.read_csv(DEMAND_PATH, dtype={"tract": str})
    hex_tract_lookup = pd.read_csv(HEX_TRACT_CACHE_PATH, dtype={"geoid": str})

    rows = []
    for week in all_weeks:
        week = pd.Timestamp(week)
        snapshot = build_point_in_time_snapshot(df, week)
        row, _ = compute_snapshot(snapshot, week, hex_tract_lookup, vacancy_df, demand_df, build_geojson=False)
        rows.append(row)
        print(f"{row['week_of']}: {row['n_listings']} listings, "
              f"{row['pct_below_ami_4p']}% below AMI, "
              f"{row['pct_conversion_feasible_only']}% conversion-only, "
              f"{row['pct_new_construction_feasible']}% new-construction feasible")

    history = pd.DataFrame(rows).sort_values("week_of")
    history.to_csv(AFFORDABILITY_HISTORY_PATH, index=False)
    print(f"\nWrote {len(history)} weeks to {AFFORDABILITY_HISTORY_PATH}")


if __name__ == "__main__":
    main()
