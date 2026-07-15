"""
Build Route Search Table
==========================
combined_schedule.csv se ek 'train_stops' table banata hai database mein.
Ye table har train ke har stop ka data rakhta hai (station, distance, timing)
- isse hum KISI BHI 2 stations ke beech route dhoond sakte hain,
  chahe wo exact pair fares_clean.csv mein ho ya na ho.
"""

import pandas as pd
import sqlite3

RAW_SCHEDULE = "data/raw/delay_data/combined_schedule.csv"
DB_PATH = "railway.db"


def build_train_stops():
    print("Loading combined_schedule.csv...")
    df = pd.read_csv(RAW_SCHEDULE)

    # Column ka naam clearer banao aur train_no ko consistent format (5-digit string) mein lao
    df = df.rename(columns={"station_name": "station_code"})
    df["train_no"] = df["train_no"].astype(str).str.zfill(5)
    df["station_code"] = df["station_code"].astype(str).str.strip().str.upper()

    # Duplicate rows hatao (agar koi ho)
    df = df.drop_duplicates(subset=["train_no", "station_no"])

    print(f"Total stops: {len(df)}")

    conn = sqlite3.connect(DB_PATH)
    df.to_sql("train_stops", conn, if_exists="replace", index=False)

    # Indexes - fast lookup ke liye (station_code pe search sabse zyada hoga)
    cursor = conn.cursor()
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_stops_station ON train_stops(station_code);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_stops_train ON train_stops(train_no);")
    conn.commit()
    conn.close()

    print("'train_stops' table created with indexes.")


if __name__ == "__main__":
    build_train_stops()