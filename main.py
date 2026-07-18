from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import pandas as pd
import random
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity as sk_cosine_similarity
from faq_data import FAQ_DATA

app = FastAPI(title="Railway Search API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "railway.db"

import os
import urllib.request

DB_DOWNLOAD_URL = "https://github.com/AayushiMohan/Smart-Railway/releases/download/v1.0.0/railway.db"

if not os.path.exists(DB_PATH):
    print("railway.db nahi mili locally - GitHub Release se download kar rahe hain...")
    urllib.request.urlretrieve(DB_DOWNLOAD_URL, DB_PATH)
    print("Database download complete.")

print("Setting up chatbot (TF-IDF)...")
faq_questions = [item["question"] for item in FAQ_DATA]
tfidf_vectorizer = TfidfVectorizer(stop_words="english")
faq_vectors = tfidf_vectorizer.fit_transform(faq_questions)
print("Chatbot ready.")


def cosine_similarity(query_vector, faq_vector):
    return sk_cosine_similarity(query_vector, faq_vector)[0][0]


@app.on_event("startup")
def ensure_bookings_table():
    """App start hote hi bookings aur analytics tables bana do agar exist nahi karte"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            pnr TEXT PRIMARY KEY,
            train_number TEXT,
            train_name TEXT,
            source TEXT,
            destination TEXT,
            journey_date TEXT,
            class_code TEXT,
            fare INTEGER,
            passenger_name TEXT,
            passenger_age INTEGER,
            passenger_gender TEXT,
            booking_time TEXT,
            status TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analytics_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT,
            details TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()


def log_event(event_type: str, details: str = ""):
    """Har important action (visit, search, booking) ko analytics table mein log karta hai"""
    from datetime import datetime
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO analytics_events (event_type, details, timestamp) VALUES (?, ?, ?)",
        (event_type, details, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()


def get_connection():
    """Har request ke liye ek naya database connection banata hai"""
    return sqlite3.connect(DB_PATH)


@app.get("/")
def read_root():
    return {"message": "Railway Search API is running!"}


@app.get("/track/visit")
def track_visit():
    """Frontend page load hote hi ye call hoga - ek 'visit' event log karta hai"""
    log_event("visit", "page loaded")
    return {"status": "logged"}


@app.get("/analytics/summary")
def analytics_summary():
    """
    Total visits, searches, aur bookings ka summary - resume/demo ke liye useful.
    Example: /analytics/summary
    """
    conn = get_connection()

    visits = pd.read_sql("SELECT COUNT(*) as c FROM analytics_events WHERE event_type = 'visit'", conn)["c"][0]
    searches = pd.read_sql("SELECT COUNT(*) as c FROM analytics_events WHERE event_type = 'search'", conn)["c"][0]
    bookings = pd.read_sql("SELECT COUNT(*) as c FROM bookings", conn)["c"][0]

    top_routes = pd.read_sql("""
        SELECT details, COUNT(*) as count
        FROM analytics_events
        WHERE event_type = 'search'
        GROUP BY details
        ORDER BY count DESC
        LIMIT 5
    """, conn)

    conn.close()

    return {
        "total_visits": int(visits),
        "total_searches": int(searches),
        "total_bookings": int(bookings),
        "top_searched_routes": top_routes.to_dict(orient="records")
    }

FARE_MODEL = {
    "2S": {"base": 20, "per_km": 0.15, "label": "Second Sitting"},
    "SL": {"base": 30, "per_km": 0.35, "label": "Sleeper"},
    "3A": {"base": 40, "per_km": 0.90, "label": "AC 3-Tier"},
    "2A": {"base": 50, "per_km": 1.30, "label": "AC 2-Tier"},
    "1A": {"base": 60, "per_km": 2.20, "label": "AC First Class"},
}


def estimate_fares(distance_km):
    """Har class ke liye estimated fare return karta hai based on distance"""
    fares = {}
    for code, info in FARE_MODEL.items():
        fare = info["base"] + info["per_km"] * distance_km
        fares[code] = {"label": info["label"], "fare": round(fare)}
    return fares


def time_to_minutes(day, time_str):
    """day + 'HH:MM' ko total minutes mein convert karta hai (Day 1 = 0 offset)"""
    if pd.isna(time_str) or pd.isna(day):
        return None
    try:
        hours, minutes = map(int, str(time_str).strip().split(":"))
        return (int(day) - 1) * 24 * 60 + hours * 60 + minutes
    except Exception:
        return None


def find_routes(source: str, destination: str):
    """
    Route-based search ka core logic - /search aur /smart-search dono
    isi function ko use karte hain, taaki code duplicate na ho.
    Returns: list of train dicts (khaali list agar kuch na mile)
    """
    conn = get_connection()

    query = """
        SELECT
            a.train_no,
            a.station_no AS src_seq, a.distance_from_origin AS src_dist,
            a.departure_day AS src_dep_day, a.departure_time AS src_dep_time,
            b.station_no AS dst_seq, b.distance_from_origin AS dst_dist,
            b.arrival_day AS dst_arr_day, b.arrival_time AS dst_arr_time
        FROM train_stops a
        JOIN train_stops b ON a.train_no = b.train_no
        WHERE a.station_code = ? AND b.station_code = ? AND a.station_no < b.station_no
    """
    routes = pd.read_sql(query, conn, params=(source, destination))

    if routes.empty:
        conn.close()
        return []

    train_nos = tuple(routes["train_no"].unique())
    placeholder = ",".join(["?"] * len(train_nos))
    trains_query = f"SELECT trainNumber, train_name, type_code FROM trains WHERE trainNumber IN ({placeholder})"
    trains_df = pd.read_sql(trains_query, conn, params=train_nos)
    conn.close()

    routes = routes.merge(trains_df, left_on="train_no", right_on="trainNumber", how="left")

    results = []
    for _, row in routes.iterrows():
        distance_km = row["dst_dist"] - row["src_dist"]
        if distance_km <= 0:
            continue

        src_minutes = time_to_minutes(row["src_dep_day"], row["src_dep_time"])
        dst_minutes = time_to_minutes(row["dst_arr_day"], row["dst_arr_time"])

        duration_hrs = None
        if src_minutes is not None and dst_minutes is not None and dst_minutes > src_minutes:
            duration_hrs = round((dst_minutes - src_minutes) / 60, 1)

        dep_hour = None
        if pd.notna(row["src_dep_time"]):
            try:
                dep_hour = int(str(row["src_dep_time"]).split(":")[0])
            except Exception:
                dep_hour = None

        results.append({
            "trainNumber": row["train_no"],
            "train_name": row["train_name"] if pd.notna(row["train_name"]) else "Unknown",
            "type_code": row["type_code"] if pd.notna(row["type_code"]) else "N/A",
            "distance_km": round(distance_km),
            "duration_hrs": duration_hrs,
            "departure_time": row["src_dep_time"] if pd.notna(row["src_dep_time"]) else None,
            "arrival_time": row["dst_arr_time"] if pd.notna(row["dst_arr_time"]) else None,
            "departure_hour": dep_hour,
            "fares": estimate_fares(distance_km)
        })

    return results

@app.get("/search")
def search_trains(source: str, destination: str):
    """
    Route-based search: kisi bhi train mein agar source aur destination
    dono stations aate hain (chahe beech mein hi kyun na ho), wo train result mein aayegi.

    Example: /search?source=NDLS&destination=PNBE
    """
    source = source.strip().upper()
    destination = destination.strip().upper()

    log_event("search", f"{source} -> {destination}")

    results = find_routes(source, destination)

    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"No trains found connecting {source} to {destination}"
        )

    results.sort(key=lambda x: x["distance_km"])

    return {
        "source": source,
        "destination": destination,
        "count": len(results),
        "trains": results
    }

@app.get("/stations/search")
def search_station(name: str):
    """
    Station naam YA address (city/state) se match karne wale SAARE stations dhoondta hai.
    Kuch bhi hide nahi hota - bas ordering aisi hai ki zyada relevant results upar aayein.
    Example: /stations/search?name=patna
    """
    conn = get_connection()
    search_term = name.strip().upper()

    query = """
        SELECT station_code, station_name, station_zone, station_address,
               CASE
                   WHEN station_name LIKE ? THEN 0
                   WHEN station_name LIKE ? THEN 1
                   ELSE 2
               END AS relevance
        FROM stations
        WHERE station_name LIKE ? OR station_address LIKE ?
        ORDER BY relevance ASC, station_name ASC
        LIMIT 100
    """
    params = (f"{search_term}%", f"%{search_term}%", f"%{search_term}%", f"%{search_term}%")

    df = pd.read_sql(query, conn, params=params)
    conn.close()

    df = df.drop(columns=["relevance"])
    return {"results": df.to_dict(orient="records")}


@app.get("/trains/{train_number}")
def get_train_detail(train_number: str):
    """
    Ek specific train ka detail dekhne ke liye.
    Example: /trains/00961
    """
    train_number = train_number.strip().zfill(5)
    conn = get_connection()

    query = "SELECT * FROM trains WHERE trainNumber = ?"
    df = pd.read_sql(query, conn, params=(train_number,))
    conn.close()

    if df.empty:
        raise HTTPException(status_code=404, detail="Train not found")

    return df.to_dict(orient="records")[0]


# ---------- BOOKING SYSTEM ----------
class BookingRequest(BaseModel):
    train_number: str
    train_name: str
    source: str
    destination: str
    journey_date: str
    class_code: str
    fare: int
    passenger_name: str
    passenger_age: int
    passenger_gender: str


def generate_pnr(conn):
    """Ek unique 10-digit PNR number generate karta hai"""
    cursor = conn.cursor()
    while True:
        pnr = str(random.randint(1000000000, 9999999999))
        cursor.execute("SELECT 1 FROM bookings WHERE pnr = ?", (pnr,))
        if cursor.fetchone() is None:
            return pnr


@app.post("/book")
def create_booking(booking: BookingRequest):
    """
    Naya booking banata hai aur ek PNR generate karta hai.
    NOTE: Ye ek MOCK/SIMULATED booking hai - koi real payment ya
    IRCTC reservation nahi hoti, sirf app ke andar record store hota hai.
    """
    from datetime import datetime

    conn = get_connection()
    pnr = generate_pnr(conn)
    booking_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO bookings (
            pnr, train_number, train_name, source, destination,
            journey_date, class_code, fare, passenger_name,
            passenger_age, passenger_gender, booking_time, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        pnr, booking.train_number, booking.train_name, booking.source, booking.destination,
        booking.journey_date, booking.class_code, booking.fare, booking.passenger_name,
        booking.passenger_age, booking.passenger_gender, booking_time, "CONFIRMED"
    ))
    conn.commit()
    conn.close()

    return {
        "pnr": pnr,
        "status": "CONFIRMED",
        "message": "Booking successful (simulated)",
        **booking.dict(),
        "booking_time": booking_time
    }


@app.get("/booking/{pnr}")
def get_booking(pnr: str):
    """PNR se booking detail retrieve karne ke liye"""
    conn = get_connection()
    query = "SELECT * FROM bookings WHERE pnr = ?"
    df = pd.read_sql(query, conn, params=(pnr,))
    conn.close()

    if df.empty:
        raise HTTPException(status_code=404, detail="Booking not found. Check your PNR.")

    return df.to_dict(orient="records")[0]


@app.get("/bookings/by-name")
def get_bookings_by_name(name: str):
    """
    Passenger naam se uski saari past bookings dhoondne ke liye
    (sabse recent booking sabse upar).
    Example: /bookings/by-name?name=Aayushi
    """
    conn = get_connection()
    query = """
        SELECT * FROM bookings
        WHERE passenger_name LIKE ?
        ORDER BY booking_time DESC
    """
    df = pd.read_sql(query, conn, params=(f"%{name.strip()}%",))
    conn.close()

    return {"count": len(df), "bookings": df.to_dict(orient="records")}

@app.get("/chatbot")
def chatbot_query(query: str):
    """
    User ka sawal TF-IDF vector mein convert karke, saare FAQ questions se
    sabse zyada similar wala dhoondta hai (cosine similarity), aur uska
    answer return karta hai.
    Example: /chatbot?query=how do I check my pnr
    """
    log_event("chatbot", query)

    query_vector = tfidf_vectorizer.transform([query])
    similarities = sk_cosine_similarity(query_vector, faq_vectors)[0]

    best_idx = int(np.argmax(similarities))
    best_score = float(similarities[best_idx])

    CONFIDENCE_THRESHOLD = 0.15
    if best_score < CONFIDENCE_THRESHOLD:
        return {
            "answer": "I don't have specific information on that. Please check the official IRCTC website or try rephrasing your question.",
            "matched_question": None,
            "confidence": round(best_score, 2)
        }

    return {
        "answer": FAQ_DATA[best_idx]["answer"],
        "matched_question": FAQ_DATA[best_idx]["question"],
        "confidence": round(best_score, 2)
    }


# ---------- NATURAL LANGUAGE SMART SEARCH ----------
import re


def extract_time_filter(query_lower):
    """Query mein time-of-day preference dhoondta hai"""
    if "overnight" in query_lower or "night" in query_lower:
        return "night"
    if "morning" in query_lower:
        return "morning"
    if "afternoon" in query_lower:
        return "afternoon"
    if "evening" in query_lower:
        return "evening"
    return None


def matches_time_filter(departure_time, filter_type):
    """Check karta hai kya ek train ka departure time requested time-window mein aata hai"""
    if not departure_time or not filter_type:
        return True
    try:
        hour = int(str(departure_time).split(":")[0])
    except Exception:
        return True

    if filter_type == "night":      
        return hour >= 20 or hour < 4
    if filter_type == "morning":
        return 4 <= hour < 12
    if filter_type == "afternoon":
        return 12 <= hour < 17
    if filter_type == "evening":
        return 17 <= hour < 20
    return True


def resolve_station_from_text(conn, text):
    """
    Free-text city/station naam se best-matching station code dhoondta hai.
    Jab multiple stations naam match karte hain (jaise 'Patna Jn' aur 'Patna Ghat'
    dono 'PATNA' se match honge), hum wo station choose karte hain jiske
    route mein SABSE ZYADA trains guzarti hain - ye major junction hone ka
    achha signal hai (chhote halts mein bahut kam trains rukti hain).
    """
    text = text.strip().upper()
    query = """
        SELECT s.station_code, COUNT(t.train_no) AS stop_count
        FROM stations s
        LEFT JOIN train_stops t ON s.station_code = t.station_code
        WHERE s.station_name LIKE ?
        GROUP BY s.station_code
        ORDER BY stop_count DESC
        LIMIT 1
    """
    df = pd.read_sql(query, conn, params=(f"%{text}%",))
    if df.empty:
        return None
    return df["station_code"].iloc[0]


@app.get("/smart-search")
def smart_search(query: str):
    """
    Natural language search - example:
    /smart-search?query=cheapest overnight train from Delhi to Patna
    """
    log_event("smart_search", query)
    query_lower = query.lower()

    match = re.search(r"from\s+(.+?)\s+to\s+(.+)", query_lower)
    if not match:
        raise HTTPException(
            status_code=400,
            detail="Please phrase your query like 'from X to Y', e.g. 'cheapest overnight train from Delhi to Patna'"
        )

    source_text = match.group(1)
    dest_text = match.group(2)

    conn = get_connection()
    source_code = resolve_station_from_text(conn, source_text)
    dest_code = resolve_station_from_text(conn, dest_text)
    conn.close()

    if not source_code or not dest_code:
        raise HTTPException(status_code=404, detail="Could not recognize the source/destination stations in your query.")

    base_result = search_trains(source_code, dest_code)
    trains = base_result["trains"]

    time_filter = extract_time_filter(query_lower)
    if time_filter:
        trains = [t for t in trains if matches_time_filter(t.get("departure_time"), time_filter)]

    sort_by = "distance"
    if any(word in query_lower for word in ["cheapest", "cheap", "budget"]):
        sort_by = "cheapest"
        trains.sort(key=lambda t: min(f["fare"] for f in t["fares"].values()))
    elif any(word in query_lower for word in ["fastest", "quickest", "quick"]):
        sort_by = "fastest"
        trains.sort(key=lambda t: (t["duration_hrs"] is None, t["duration_hrs"] or 999))

    if not trains:
        raise HTTPException(
            status_code=404,
            detail="No trains matched your specific preferences (time of day). Try a broader query."
        )

    return {
        "parsed": {
            "source": source_code,
            "destination": dest_code,
            "time_filter": time_filter,
            "sort_by": sort_by
        },
        "count": len(trains),
        "trains": trains
    }
