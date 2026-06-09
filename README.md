# CTR Processing Tool — Backend

## Stack
Python 3.11+, FastAPI, SQLAlchemy, SQLite (dev) / Postgres (prod), openpyxl, pandas

## Project structure
```
CRM/
├── app/
│   ├── main.py                  # app factory, startup hooks
│   ├── config.py                # Settings (reads .env)
│   ├── api/v1/
│   │   ├── router.py            # aggregates all endpoint routers
│   │   └── endpoints/
│   │       ├── campaigns.py     # GET/POST /api/campaigns, DELETE/PATCH by-id
│   │       ├── process.py       # POST /api/process  ← main upload/download
│   │       ├── settings.py      # GET/PUT /api/settings
│   │       └── memory.py        # GET /api/memory/summary, DELETE /api/memory
│   ├── db/
│   │   ├── base.py              # SQLAlchemy engine + Base
│   │   ├── session.py           # get_db dependency
│   │   └── init_db.py           # create_all + column migrations
│   ├── models/campaign.py       # GlobalSettings, CampaignRule, YesterdayMemory
│   ├── schemas/
│   │   ├── campaign.py          # CampaignRuleCreate, CampaignRuleResponse
│   │   └── settings.py          # GlobalSettingsSchema
│   └── services/
│       ├── processor.py         # CTR / VCR / Viewability processing logic
│       ├── excel_writer.py      # openpyxl Excel output builder
│       └── memory.py            # load/save yesterday snapshot
├── tests/
│   └── test_campaigns.py
├── frontend/index.html          # served at /
├── data/ctr_app.db              # SQLite DB (auto-created)
├── .env.example
├── requirements.txt
├── Procfile
└── run.py                       # python run.py → uvicorn with reload
```

## Quick start
```bash
cd CRM
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt

cp .env.example .env
python run.py                 # → http://localhost:8000
```

## API docs
- Swagger → http://localhost:8000/docs
- ReDoc   → http://localhost:8000/redoc

## Key endpoints
| Method | URL | Description |
|--------|-----|-------------|
| POST | `/api/process` | Upload xlsx/csv → download processed Excel |
| GET  | `/api/campaigns` | List all campaign rules |
| POST | `/api/campaigns` | Add / update a campaign rule |
| DELETE | `/api/campaigns/by-id/{id}` | Delete a rule |
| PATCH | `/api/campaigns/by-id/{id}/toggle` | Enable / disable a rule |
| GET  | `/api/settings` | Read global CTR defaults |
| PUT  | `/api/settings` | Update global CTR defaults |

## Run tests
```bash
pip install pytest httpx
pytest tests/
```
