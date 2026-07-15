"""
Diagnostic Script - Valid route pairs dhoondta hai jinke liye
fare data available hai, taaki tum unhi se /search test kar sako.
"""

import sqlite3
import pandas as pd

conn = sqlite3.connect("railway.db")

print("="*60)
print("Sample valid FROM -> TO station pairs (with fare data)")
print("="*60)

query = """
    SELECT DISTINCT fromStnCode, toStnCode, COUNT(*) as num_trains
    FROM fares
    GROUP BY fromStnCode, toStnCode
    ORDER BY num_trains DESC
    LIMIT 15
"""
result = pd.read_sql(query, conn)
print(result)

print("\n" + "="*60)
print("Checking if any Patna (PNBE) routes exist in fares data")
print("="*60)

patna_query = """
    SELECT DISTINCT fromStnCode, toStnCode
    FROM fares
    WHERE fromStnCode = 'PNBE' OR toStnCode = 'PNBE'
    LIMIT 15
"""
patna_result = pd.read_sql(patna_query, conn)
print(f"Routes involving PNBE: {len(patna_result)}")
print(patna_result)

conn.close()