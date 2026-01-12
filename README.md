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
- Form analytics from Google Form responses: dynamic tank counts, zivud gap aggregation, ammo per-tank averages, and Excel exports for platoon/battalion snapshots.
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
- GET `/queries/forms/summary`
- GET `/queries/forms/status`
- GET `/insights`
- GET `/health`

OAuth + Google Sheets:
- `/auth/google/callback` exchanges code -> stores short-lived session (in-memory) with access/refresh token + state (platoon/viewMode) and redirects to `/app/?token=<session_id>`.
- `/sync/google` will use the user session when header `X-OAuth-Session: <session_id>` is provided, otherwise falls back to service account/API key as configured.

### Frontend (React dashboard)
```bash
cd frontend-app
npm install
npm run dev   # open http://localhost:5173
# Set API base in the header field (defaults to http://localhost:8000). Token/Basic can be entered there and is stored locally.
# Sync button will attempt Google Sheets; or upload files from the dashboard. Choose Battalion/Platoon mode and apply filters (week/platoon/section).
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

### Shortcuts (scripts/)
- `scripts/dev-api.sh` — run API with autoreload, serves built UI at `/app` if `frontend-app/dist` exists.
- `scripts/dev-ui.sh` — run frontend dev server (use alongside dev-api in another terminal).
- `scripts/build-ui.sh` — build frontend for serving via API.
- `scripts/test.sh` — run pytest with `PYTHONPATH=src` and token cleared (override `SECURITY__API_TOKEN` if needed).
- `scripts/clean-db.sh` — remove `data/ironview.db` and sync cache/temp folders to start fresh.
- `scripts/seed-and-export.sh` — reset DB, import sample fixtures from `docs/Files/`, and emit platoon/battalion Excel reports into `reports/`.
- `scripts/sync-and-export.sh` — reset DB, sync from Google Sheets when enabled (fallback to local samples), then export platoon/battalion reports.
- Suggested QA: `scripts/clean-db.sh` → import/upload or `scripts/sync-and-export.sh` → UI smoke (Battalion/Platoon views, filters) → `scripts/test.sh`.

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
  - `SECURITY__API_TOKEN` or `SECURITY__BASIC_USER/BASIC_PASS` to require auth (imports/sync always enforce when set; queries opt-in via `REQUIRE_AUTH_ON_QUERIES`). UI includes a local token field.
  - `GOOGLE__ENABLED` + `SERVICE_ACCOUNT_FILE` or `API_KEY` + `FILE_IDS` for Sheets sync; cache and retry settings included.
  - `AI__ENABLED` + provider settings; defaults to offline simulated insights.
  - `PATHS__DB_PATH` to override DB location (default `data/ironview.db`).
- Config uses nested env keys with `__` delimiter (Pydantic Settings).
- Frontend API base: header input stored in `localStorage` (`IRONVIEW_API`).
- Field aliases/normalization live in `config/fields.yaml` (gap/ok tokens, header wildcards, platoon inference). Per-import schema snapshots are stored in DB + `data/input/schema_snapshots/`.

### Auth
- When `SECURITY__API_TOKEN` is set, all imports/sync/queries require `Authorization: Bearer <token>` (or `X-API-Key`). Basic auth is also supported via `SECURITY__BASIC_USER/BASIC_PASS`.
- The frontend shows a banner on unauthorized responses; set the token in the header field or in your HTTP client (curl/Postman).
- Smoke: without token, `/imports/*` and `/sync/google` should 401; with `SECURITY__API_TOKEN=secret`, `curl -H "Authorization: Bearer secret" ...` should succeed.

Auth smoke checklist (manual):
- Start the API with `SECURITY__API_TOKEN=secret`.
- `curl -f -H "Authorization: Bearer secret" -F file=@docs/Files/דוחות\ פלוגת\ כפיר.xlsx http://localhost:8000/imports/platoon-loadout` → expect 200.
- `curl -f http://localhost:8000/imports/platoon-loadout` → expect 401.
- UI: set the token in the header field, upload a file, run sync; clear token to confirm unauthorized banner.


### Security Checklist (Production)
- [ ] Ensure `SECURITY__API_TOKEN` is set to a strong secret in `.env`.
- [ ] If Google Sync is enabled (`GOOGLE__ENABLED=true`), ensure `service_account.json` is present but **NOT** committed.
- [ ] Verify `GOOGLE__FILE_IDS` are correct for the target deployment.
- [ ] Confirm `AI__ENABLED` is false unless explicitly required and cost-controlled.

## 📄 License
Internal Use Only - Battalion 74.
