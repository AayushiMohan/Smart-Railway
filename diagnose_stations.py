"""
Diagnostic Script - Check karta hai ki Patna/Bihar stations
raw data mein hain ya nahi, aur agar hain to processed/database
mein kahan gayab ho gaye.
"""

import pandas as pd
import sqlite3

print("="*60)
print("STEP 1: Raw file mein check karo (station_full_names.csv)")
print("="*60)
raw = pd.read_csv("data/raw/delay_data/station_full_names.csv")
print(f"Total rows in raw file: {len(raw)}")
print(f"Columns: {list(raw.columns)}")

patna_raw = raw[raw['station_full_name'].str.contains("PATNA", case=False, na=False)]
print(f"\n'PATNA' matches in RAW file: {len(patna_raw)}")
print(patna_raw.head(10))

bihar_raw = raw[raw['station_zone'].str.contains("BIHAR", case=False, na=False)] if 'station_zone' in raw.columns else pd.DataFrame()
print(f"\n'BIHAR' matches in station_zone (raw): {len(bihar_raw)}")


print("\n" + "="*60)
print("STEP 2: Processed file mein check karo (stations_clean.csv)")
print("="*60)
processed = pd.read_csv("data/processed/stations_clean.csv")
print(f"Total rows in processed file: {len(processed)}")

patna_processed = processed[processed['station_name'].str.contains("PATNA", case=False, na=False)]
print(f"\n'PATNA' matches in PROCESSED file: {len(patna_processed)}")
print(patna_processed.head(10))


print("\n" + "="*60)
print("STEP 3: Database mein check karo (railway.db)")
print("="*60)
conn = sqlite3.connect("railway.db")
query = "SELECT * FROM stations WHERE station_name LIKE '%PATNA%'"
db_result = pd.read_sql(query, conn)
print(f"'PATNA' matches in DATABASE: {len(db_result)}")
print(db_result)

# Total station count in DB
total_query = "SELECT COUNT(*) as total FROM stations"
total_in_db = pd.read_sql(total_query, conn)
print(f"\nTotal stations in database: {total_in_db['total'][0]}")

conn.close()