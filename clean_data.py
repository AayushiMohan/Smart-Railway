"""
Data Cleaning & Merging Script - Railway App Project
======================================================
Ye script raw data ko clean karke, merge karke,
data/processed/ folder mein final files save karta hai.

Output files:
1. stations_clean.csv   -> saari stations ka master list (code, name, zone, amenities)
2. trains_clean.csv     -> saari trains ka master list (number, name, type)
3. fares_clean.csv      -> route + fare + availability + duration (search ke liye main dataset)
"""

import pandas as pd
import os

# ---------- SETUP ----------
RAW = "data/raw"
PROCESSED = "data/processed"
os.makedirs(PROCESSED, exist_ok=True)


# ---------- STEP 1: STATIONS MASTER ----------
def build_stations_master():
    print("Building stations master...")

    # Bada, complete station list (code -> full name, zone, address)
    stations_full = pd.read_csv(f"{RAW}/delay_data/station_full_names.csv")
    stations_full = stations_full.rename(columns={
        "station_name": "station_code",       # ye field actually CODE hai, naam confusing hai
        "station_full_name": "station_name"   # ye asli naam hai
    })

    # Chhota dataset jisme amenities (food/hospital/lat-lng) hai
    stations_amenities = pd.read_csv(f"{RAW}/station_codes/railway_stations.csv")
    stations_amenities = stations_amenities[[
        "station_code", "lat", "lng", "platform_number",
        "food_available", "hotel_available", "hospital_available"
    ]]

    # Merge: left join taaki saari 8963 stations rahein, amenities jahan mile wahan add ho
    merged = stations_full.merge(stations_amenities, on="station_code", how="left")

    # Clean up
    merged["station_code"] = merged["station_code"].astype(str).str.strip().str.upper()
    merged["station_name"] = merged["station_name"].astype(str).str.strip()
    merged = merged.drop_duplicates(subset="station_code")

    merged.to_csv(f"{PROCESSED}/stations_clean.csv", index=False)
    print(f"  -> Saved {len(merged)} stations to stations_clean.csv")
    return merged


# ---------- STEP 2: TRAINS MASTER ----------
def build_trains_master():
    print("Building trains master...")

    trains = pd.read_csv(f"{RAW}/delay_data/train_details.csv")
    trains = trains.rename(columns={"train_no": "trainNumber"})
    trains["trainNumber"] = trains["trainNumber"].astype(str).str.zfill(5)
    trains = trains.drop_duplicates(subset="trainNumber")

    trains.to_csv(f"{PROCESSED}/trains_clean.csv", index=False)
    print(f"  -> Saved {len(trains)} trains to trains_clean.csv")
    return trains


# ---------- STEP 3: FARES + AVAILABILITY (main search dataset) ----------
def build_fares_master(trains_df):
    print("Building fares + availability dataset...")

    fares = pd.read_csv(f"{RAW}/prices_availability/price_data.csv")

    # trainNumber ko consistent string format mein lao (zfill se leading zero preserve hoga)
    fares["trainNumber"] = fares["trainNumber"].astype(str).str.zfill(5)

    # Sirf useful columns rakho search ke liye
    keep_cols = [
        "trainNumber", "fromStnCode", "toStnCode", "classCode",
        "totalFare", "baseFare", "tatkalFare", "availability",
        "distance", "duration"
    ]
    fares = fares[keep_cols]

    # Station codes ko clean karo
    fares["fromStnCode"] = fares["fromStnCode"].astype(str).str.strip().str.upper()
    fares["toStnCode"] = fares["toStnCode"].astype(str).str.strip().str.upper()

    # Train type/name merge karo taaki pata chale kaunsi train hai
    fares = fares.merge(trains_df[["trainNumber", "train_name", "type_code"]],
                         on="trainNumber", how="left")

    # Duplicate rows hatao (agar same route+class+time repeat ho raha ho)
    fares = fares.drop_duplicates()

    fares.to_csv(f"{PROCESSED}/fares_clean.csv", index=False)
    print(f"  -> Saved {len(fares)} fare records to fares_clean.csv")
    return fares


# ---------- RUN EVERYTHING ----------
if __name__ == "__main__":
    stations_df = build_stations_master()
    trains_df = build_trains_master()
    fares_df = build_fares_master(trains_df)

    print("\n" + "=" * 50)
    print("DONE! Check data/processed/ folder for:")
    print("  - stations_clean.csv")
    print("  - trains_clean.csv")
    print("  - fares_clean.csv")
    print("=" * 50)

    # Quick sanity check - kitne trains ka fare data mila match?
    matched = fares_df["train_name"].notnull().sum()
    total = len(fares_df)
    print(f"\nSanity check: {matched}/{total} fare rows matched with a known train name")