import sqlite3
import pandas as pd

conn = sqlite3.connect("railway.db")
print("="*60)
print("Check 1: NDLS ke liye ab exactly kya naam stored hai?")
print("="*60)
q1 = "SELECT * FROM stations WHERE station_code = 'NDLS'"
print(pd.read_sql(q1, conn))
print("\n" + "="*60)
print("Check 2: 'delhi' search karne pe FULL ranked list (jaisa API dikhati)")
print("="*60)
search_term = "DELHI"
query = """
    SELECT station_code, station_name, station_zone,
           CASE
               WHEN station_name LIKE ? THEN 0
               WHEN station_name LIKE ? THEN 1
               ELSE 2
           END AS relevance
    FROM stations
    WHERE station_name LIKE ? OR station_address LIKE ?
    ORDER BY relevance ASC, station_name ASC
"""
params = (f"{search_term}%", f"%{search_term}%", f"%{search_term}%", f"%{search_term}%")
full_result = pd.read_sql(query, conn, params=params)
print(f"Total matches (no limit): {len(full_result)}")
print(full_result.head(45).to_string())
print("\n" + "="*60)
print("Check 3: NDLS ka position kahan hai is list mein?")
print("="*60)
if 'NDLS' in full_result['station_code'].values:
    position = full_result[full_result['station_code'] == 'NDLS'].index[0]
    print(f"NDLS is at position: {position + 1} (out of {len(full_result)} total matches)")
else:
    print("NDLS is NOT in the results at all!")

conn.close()