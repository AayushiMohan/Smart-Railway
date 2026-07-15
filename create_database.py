"""
Create Database Script - Railway App Project
==============================================
Ye script data/processed/ ki teeno clean CSV files ko
SQLite database mein convert karta hai, taaki FastAPI
backend fast queries kar sake.

Output: railway.db (SQLite database file, root folder mein banega)
"""

import pandas as pd
import sqlite3
import os

PROCESSED = "data/processed"
DB_PATH = "railway.db"


def create_database():
    print("Connecting to SQLite database...")
    conn = sqlite3.connect(DB_PATH)

    # ---------- STATIONS TABLE ----------
    print("Loading stations_clean.csv...")
    stations_df = pd.read_csv(f"{PROCESSED}/stations_clean.csv")
    stations_df.to_sql("stations", conn, if_exists="replace", index=False)
    print(f"  -> 'stations' table created with {len(stations_df)} rows")

    # ---------- TRAINS TABLE ----------
    print("Loading trains_clean.csv...")
    trains_df = pd.read_csv(f"{PROCESSED}/trains_clean.csv")
    # trainNumber ko text rakho taaki leading zeros preserve rahein
    trains_df["trainNumber"] = trains_df["trainNumber"].astype(str).str.zfill(5)
    trains_df.to_sql("trains", conn, if_exists="replace", index=False)
    print(f"  -> 'trains' table created with {len(trains_df)} rows")

    # ---------- FARES TABLE ----------
    print("Loading fares_clean.csv...")
    fares_df = pd.read_csv(f"{PROCESSED}/fares_clean.csv")
    fares_df["trainNumber"] = fares_df["trainNumber"].astype(str).str.zfill(5)
    fares_df.to_sql("fares", conn, if_exists="replace", index=False)
    print(f"  -> 'fares' table created with {len(fares_df)} rows")

    # ---------- CREATE INDEXES (fast search ke liye) ----------
    print("\nCreating indexes for fast search...")
    cursor = conn.cursor()

    # Station code pe search fast karne ke liye
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_station_code ON stations(station_code);")

    # Train number pe search fast karne ke liye
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_train_number ON trains(trainNumber);")

    # Fares table mein from-to station pe search sabse zyada hoga, isliye ye sabse important index hai
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_from_to ON fares(fromStnCode, toStnCode);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fares_train ON fares(trainNumber);")

    conn.commit()
    print("  -> Indexes created")

    conn.close()
    print(f"\n{'='*50}")
    print(f"DONE! Database created at: {DB_PATH}")
    print(f"{'='*50}")


def test_database():
    """Quick test - ek sample query chala ke dekhte hain database kaam kar raha hai"""
    print("\nRunning a test query...")
    conn = sqlite3.connect(DB_PATH)

    # Test: kisi bhi 2 stations ke beech ke pehle 5 fare records dikhao
    query = """
        SELECT trainNumber, train_name, fromStnCode, toStnCode,
               classCode, totalFare, availability
        FROM fares
        LIMIT 5;
    """
    result = pd.read_sql(query, conn)
    print(result)

    conn.close()


if __name__ == "__main__":
    create_database()
    test_database()