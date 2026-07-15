"""
Data Exploration Script - Railway App Project
Ye script har dataset ko load karke uska structure dikhata hai:
- Kitni rows/columns hain
- Column names kya hain
- Sample data kaisa dikhta hai
- Missing values kitne hain
"""

import pandas as pd
import json
import os

def explore_csv(filepath):
    """CSV file ko explore karta hai"""
    print(f"\n{'='*60}")
    print(f"FILE: {filepath}")
    print(f"{'='*60}")
    try:
        df = pd.read_csv(filepath)
        print(f"Shape (rows, columns): {df.shape}")
        print(f"\nColumn Names:\n{list(df.columns)}")
        print(f"\nFirst 3 rows:\n{df.head(3)}")
        print(f"\nMissing values per column:\n{df.isnull().sum()}")
        print(f"\nData types:\n{df.dtypes}")
    except Exception as e:
        print(f"ERROR reading file: {e}")


def explore_json(filepath):
    """JSON file ko explore karta hai"""
    print(f"\n{'='*60}")
    print(f"FILE: {filepath}")
    print(f"{'='*60}")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if isinstance(data, list):
            print(f"Type: List with {len(data)} items")
            if len(data) > 0:
                print(f"\nFirst item structure:\n{json.dumps(data[0], indent=2)[:1000]}")
        elif isinstance(data, dict):
            print(f"Type: Dictionary with keys: {list(data.keys())}")
            # Print a sample of the first key's content
            first_key = list(data.keys())[0]
            print(f"\nSample content of key '{first_key}':")
            print(json.dumps(data[first_key], indent=2)[:1000])
    except Exception as e:
        print(f"ERROR reading file: {e}")


def explore_folder(folder_path):
    """Ek folder ke andar saari CSV/JSON files explore karta hai"""
    if not os.path.exists(folder_path):
        print(f"Folder not found: {folder_path}")
        return

    files = os.listdir(folder_path)
    if not files:
        print(f"Folder is empty: {folder_path}")
        return

    for file in files:
        filepath = os.path.join(folder_path, file)
        if file.endswith('.csv'):
            explore_csv(filepath)
        elif file.endswith('.json'):
            explore_json(filepath)
        else:
            print(f"\nSkipping (not CSV/JSON): {file}")


if __name__ == "__main__":
    # Base data folder path (adjust if your structure is different)
    base_path = "data/raw"

    folders_to_check = [
        "schedule_routes",
        "prices_availability",
        "station_codes",
        "delay_data"
    ]

    for folder in folders_to_check:
        full_path = os.path.join(base_path, folder)
        print(f"\n\n{'#'*60}")
        print(f"# EXPLORING FOLDER: {folder}")
        print(f"{'#'*60}")
        explore_folder(full_path)