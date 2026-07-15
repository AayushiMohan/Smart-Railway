"""
Rebuild Stations Master - One-Time Comprehensive Fix
=======================================================
Problem: 'stations' table aur 'train_stops' table alag-alag datasets se
bane the, isliye kuch codes (jaise NDLS) routes mein the lekin naam-table
mein missing the (ya ulta) - is wajah se search mein gaps aa rahe the.

Solution: 'train_stops' mein jo bhi station codes ACTUALLY use ho rahe hain
(guaranteed-working codes) unke liye, teen alag sources se naam dhoondo aur
best available naam use karo. Isse ek single, fully-connected stations
table banega jo search aur route-search dono ke saath consistent hoga.
"""

import json
import os
import pandas as pd
import sqlite3

RAW = "data/raw"
DB_PATH = "railway.db"


def parse_schedule_jsons():
    """
    EXP/PASS/SF-TRAINS.json files mein har stop ka 'stationName' field
    format mein hota hai: "STATION NAME - CODE" (jaise "MARWAR JN - MJ")
    Isse code -> name mapping nikalte hain - ye source sabse reliable hai
    kyunki ye seedha train route data se aata hai.
    """
    name_map = {}
    files = ["EXP-TRAINS.json", "PASS-TRAINS.json", "SF-TRAINS.json"]

    for fname in files:
        path = f"{RAW}/schedule_routes/{fname}"
        if not os.path.exists(path):
            print(f"  (skip - not found: {path})")
            continue
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for train in data:
            for stop in train.get("trainRoute", []):
                raw_name = stop.get("stationName", "")
                if " - " in raw_name:
                    name, code = raw_name.rsplit(" - ", 1)
                    code = code.strip().upper()
                    name = name.strip()
                    if code and name:
                        name_map[code] = name

    return name_map


def build_master_stations():
    conn = sqlite3.connect(DB_PATH)

    # ---------- AUTHORITATIVE CODE LIST ----------
    # Ye wo codes hain jo ACTUALLY kisi train ke route mein use hote hain
    codes_df = pd.read_sql("SELECT DISTINCT station_code FROM train_stops", conn)
    codes_in_routes = codes_df["station_code"].str.upper().tolist()
    print(f"Total unique station codes used in real train routes: {len(codes_in_routes)}")

    # ---------- NAME SOURCE A: station_full_names.csv ----------
    full_names = pd.read_csv(f"{RAW}/delay_data/station_full_names.csv")
    full_names = full_names.rename(columns={
        "station_name": "station_code",
        "station_full_name": "station_name"
    })
    full_names["station_code"] = full_names["station_code"].astype(str).str.upper()
    name_a = dict(zip(full_names["station_code"], full_names["station_name"]))
    address_map = dict(zip(full_names["station_code"], full_names["station_address"]))
    zone_map = dict(zip(full_names["station_code"], full_names["station_zone"]))

    # ---------- NAME SOURCE B: railway_stations.csv (chhota but high quality) ----------
    amenities_df = pd.read_csv(f"{RAW}/station_codes/railway_stations.csv")
    amenities_df["station_code"] = amenities_df["station_code"].astype(str).str.upper()
    name_b = dict(zip(amenities_df["station_code"], amenities_df["station_name"]))

    # ---------- NAME SOURCE C: schedule JSONs (sabse reliable, route data se hi aaya) ----------
    print("Parsing schedule JSON files for station names...")
    name_c = parse_schedule_jsons()
    print(f"Name sources found -> A: {len(name_a)}, B: {len(name_b)}, C: {len(name_c)}")

    # ---------- BUILD FINAL MASTER ----------
    # Priority: C (route JSON) > B (curated list) > A (bulk dataset) > fallback to code itself
    rows = []
    missing_count = 0
    for code in codes_in_routes:
        name = name_c.get(code) or name_b.get(code) or name_a.get(code)
        if not name:
            name = code  # kahin se bhi naam nahi mila, to code hi dikhado (better than nothing)
            missing_count += 1
        rows.append({
            "station_code": code,
            "station_name": name,
            "station_zone": zone_map.get(code, ""),
            "station_address": address_map.get(code, "")
        })

    print(f"Stations with NO name in any source (fallback used): {missing_count}")

    master = pd.DataFrame(rows).drop_duplicates(subset="station_code")

    # Amenities merge karo jahan available ho
    amenities_cols = amenities_df[[
        "station_code", "lat", "lng", "platform_number",
        "food_available", "hotel_available", "hospital_available"
    ]]
    master = master.merge(amenities_cols, on="station_code", how="left")

    # ---------- SAVE ----------
    master.to_sql("stations", conn, if_exists="replace", index=False)
    cursor = conn.cursor()
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_station_code ON stations(station_code);")
    conn.commit()
    conn.close()

    print(f"\nDONE. Rebuilt 'stations' table with {len(master)} rows.")
    print("Every station here is GUARANTEED to have real route data too.")


if __name__ == "__main__":
    build_master_stations()