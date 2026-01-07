# Iron-View: Tactical Readiness System

> **Battalion 74 | Operational Dashboard**  
> *A specialized, offline-first command system for tracking vehicle readiness, logistics, and intelligence.*

![Iron-View Dashboard](https://via.placeholder.com/800x400?text=Iron-View+Tactical+Dashboard)

## 🎯 Overview

Iron-View ingests the weekly company/battalion spreadsheets (platoon loadout, battalion summary, form responses), normalizes them into SQLite, exposes deterministic queries via FastAPI, and serves a local dashboard (React + Chart.js). Offline-first by default; optional future sync from Google Sheets.

The system replaces manual Excel crunching with immediate operational insights.

## ✨ Features

- Adapters for platoon loadout, battalion summary, and Google Form responses (xlsx).
- SQLite persistence with hash-based idempotent imports and raw capture.
- Deterministic queries: totals, gaps, by-platoon, delta (last two imports), variance vs battalion summary, form status counts.
- FastAPI endpoints for uploads, queries, Google Sheets sync (with retry/cache), and AI insights.
- React (Vite) dashboard consuming the API, with filters, sortable tables for delta/variance, trends, and AI insight panel.
- Offline-first: all assets local; CORS enabled for local dev.

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node 18+ (for frontend dev/build)
- Optional: Docker/Docker Compose

### Backend (API + ingestion)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# configure env (copy .env.example -> .env and adjust)
uvicorn iron_view.api.main:app --reload --port 8000
```

Endpoints:
- POST `/imports/platoon-loadout` (file)
- POST `/imports/battalion-summary` (file)
- POST `/imports/form-responses` (file)
- POST `/sync/google?target=all|platoon_loadout|battalion_summary|form_responses`
- GET `/sync/status`
- GET `/queries/tabular/totals|gaps|by-platoon|delta|variance`
- GET `/queries/trends`
- GET `/queries/forms/status`
- GET `/insights`
- GET `/health`

### Frontend (React dashboard)
```bash
cd frontend-app
npm install
npm run dev   # open http://localhost:5173
# set API base in the header (defaults to http://localhost:8000). Filters include section/platoon/sort.
```
To build static assets:
```bash
npm run build   # outputs to frontend-app/dist
```

Static frontend serve (Option A):
- Build: `cd frontend-app && npm run build`
- API will serve the built UI at `/app` when `frontend-app/dist` exists.

Dev mode (Option B):
- Run API as above, and `npm run dev` in `frontend-app` (defaults to http://localhost:5173 with CORS).

### Docker (optional)
```bash
docker compose build
docker compose up
# API at http://localhost:8000 , UI at http://localhost:8000/app (after build)
```

## 🏗️ Architecture

```
iron-view/
├── src/iron_view/
│   ├── config.py       # settings (paths, imports, thresholds)
│   ├── domain/         # Pydantic models
│   ├── etl/            # Adapters & loader
│   ├── data/           # DTOs, storage (SQLite), import service
│   ├── services/       # Query service (deterministic)
│   ├── api/            # FastAPI app factory (serves /app if built)
│   └── logic/          # analyzers/rule-based AI
├── frontend-app/       # Vite React dashboard (consumes API, build -> /app)
└── tests/              # unit/integration tests
```

## 🛠️ Configuration
- Copy `.env.example` to `.env` and adjust:
  - `SECURITY__API_TOKEN` or `SECURITY__BASIC_USER/BASIC_PASS` to require auth (imports/sync always enforce when set; queries opt-in via `REQUIRE_AUTH_ON_QUERIES`).
  - `GOOGLE__ENABLED` + `SERVICE_ACCOUNT_FILE` or `API_KEY` + `FILE_IDS` for Sheets sync; cache and retry settings included.
  - `AI__ENABLED` + provider settings; defaults to offline simulated insights.
  - `PATHS__DB_PATH` to override DB location (default `data/ironview.db`).
- Config uses nested env keys with `__` delimiter (Pydantic Settings).
- Frontend API base: header input stored in `localStorage` (`IRONVIEW_API`).

## 📄 License
Internal Use Only - Battalion 74.
