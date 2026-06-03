# CTR Processing Tool

Python + FastAPI + React port of the n8n workflow.

## Project Structure

```
CRM/
├── backend/
│   ├── main.py          ← FastAPI app (API routes)
│   ├── processor.py     ← Core CTR/VCR/Viewability logic
│   ├── database.py      ← SQLite via SQLAlchemy
│   └── requirements.txt
├── frontend/
│   └── index.html       ← React UI (no build step needed)
└── README.md
```

## Setup & Run

### 1. Install dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Start the server

```bash
cd backend
uvicorn main:app --reload
```

The app runs at **http://localhost:8000**

The frontend is served automatically at http://localhost:8000/

### 3. Use it

- Open http://localhost:8000 in your browser
- **Upload & Process tab** — drag-drop your Excel/CSV, click Process & Download
- **Campaign CTR Rules tab** — add per-campaign CTR overrides
- **Settings tab** — change the global CTR range and manage yesterday memory

---

## Features

| Feature | Details |
|---|---|
| CTR calculation | Random clicks within Min–Max CTR %, deduped against yesterday |
| Per-campaign CTR override | Set different ranges per Line Item ID |
| Global CTR range | Default 0.37% – 0.55%, configurable |
| Video Completion Rate | Kept 75%–89% of Start Views |
| Viewability | Viewable Impressions 75%–89% of Measurable |
| Yesterday memory | Stored in SQLite, prevents duplicate CTR across runs |
| Date normalisation | Excel serial dates and all common formats → DD/MM/YYYY |

## Database

SQLite file `backend/ctr_app.db` is created automatically on first run.

Tables:
- `global_settings` — one row, min/max CTR
- `campaign_rules` — per Line Item CTR overrides
- `yesterday_memory` — last run's click/CTR snapshot

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| POST | /api/process | Upload file → get processed Excel |
| GET | /api/settings | Get global CTR range |
| PUT | /api/settings | Update global CTR range |
| GET | /api/campaigns | List all campaign rules |
| POST | /api/campaigns | Add or update a campaign rule |
| DELETE | /api/campaigns/{id} | Delete a campaign rule |
| PATCH | /api/campaigns/{id}/toggle | Enable/disable a rule |
| GET | /api/memory/summary | View yesterday memory |
| DELETE | /api/memory | Clear yesterday memory |
