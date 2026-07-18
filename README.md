# 🚆 Railway Smart Search & Booking System

A full-stack Railway Search, Booking, Analytics, and RAG-based Chatbot application built using FastAPI, SQLite, HTML, CSS, and JavaScript.

## 📌 Features:

### Smart Train Search
- Search trains between any source and destination station.
- Route-based train discovery using railway schedule data.
- Train details including:
  - Distance
  - Duration
  - Departure & Arrival Time
  - Estimated fares

### Simulated Ticket Booking
- Passenger booking form
- Automatic PNR generation
- Booking history retrieval
- PNR-based booking lookup

### Analytics Dashboard
- Track visits
- Track train searches
- Track bookings
- Most searched routes

### Railway Assistant Chatbot
- Built using Sentence Transformers
- Semantic similarity search
- FAQ retrieval system
- Confidence-based response ranking

### Natural Language Search
Examples:

- "Cheapest train from Delhi to Patna"
- "Fastest train from Mumbai to Chennai"
- "Overnight train from Delhi to Patna"

---

## Tech Stack

### Backend
- FastAPI
- SQLite
- Pandas
- NumPy
- Sentence Transformers

### Frontend
- HTML
- CSS
- JavaScript

### Machine Learning / NLP
- all-MiniLM-L6-v2
- Cosine Similarity
- Semantic Search

---

## Dataset

This project utilizes railway data derived and processed from publicly available railway schedule datasets.

Data was cleaned, transformed, and structured into:

- Trains
- Stations
- Train Stops
- Routes
- Distance Information

The database is stored locally using SQLite.

---

## RAG-Style Retrieval Pipeline

User Query
↓
Sentence Embedding
↓
Semantic Similarity Search
↓
Best Matching FAQ Retrieval
↓
Response Generation

---

## Future Enhancements

- Full LLM-powered RAG generation
- Live train status integration
- Real-time seat availability
- User authentication
- Cloud database deployment

---
