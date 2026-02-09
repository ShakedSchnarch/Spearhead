# Spearhead (Responses-Only v1)

Spearhead is now focused on a single source of truth: **form responses**.
The system ingests response events, normalizes them, builds read models, and exposes consistent query endpoints for the dashboard.

## What Changed

- Responses-only boundary: no battalion/platoon spreadsheet ingestion in the active contract.
- New versioned API under `/v1/*`.
- Export endpoints are deprecated and return `410`.
- UI is simplified to library-based grids (Mantine + `mantine-datatable`) and server-driven queries.

## Project Structure

- Active architecture reference: `docs/ARCHITECTURE.md`
- Operational runbook: `docs/RUNBOOK.md`
- Cloud setup: `docs/cloud/SETUP_STAGE_A.md`
- Historical plans/samples: `docs/archive/`

## Active API (v1)

- `POST /v1/ingestion/forms/events`
- `GET /v1/metrics/overview?week=YYYY-Www`
- `GET /v1/metrics/platoons/{platoon}?week=YYYY-Www`
- `GET /v1/metrics/tanks?platoon=...&week=...`
- `GET /v1/queries/gaps?week=...&platoon=...&group_by=item|tank|family`
- `GET /v1/queries/trends?metric=reports|total_gaps|gap_rate|distinct_tanks&window_weeks=...&platoon=...`
- `GET /v1/queries/search?q=...&week=...&platoon=...`
- `GET /v1/metadata/weeks?platoon=...`

## Deprecated API

- `GET /exports/platoon` -> `410 Gone`
- `GET /exports/battalion` -> `410 Gone`
- `POST /imports/platoon-loadout` -> `410 Gone`
- `POST /imports/battalion-summary` -> `410 Gone`
- `POST /imports/form-responses` -> `410 Gone`

If you still need old query/intelligence routes for a migration window, set `APP__ENABLE_LEGACY_ROUTES=true`.

## Local Run

### One-click (recommended)

```bash
./scripts/dev-one-click.sh
```

Or:

```bash
make dev
```

This runs everything from one terminal:
- builds frontend only when needed
- runs FastAPI on `http://127.0.0.1:8000`
- serves the UI from `/spearhead/`

### Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src uvicorn spearhead.api.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend-app
npm install
npm run dev
npm run build
```

Frontend is intentionally single-flow now: one login screen and one dashboard screen (no router/context/layered layouts).

### Tests (non-legacy)

```bash
./scripts/test.sh
```

To include legacy tests explicitly:

```bash
./scripts/test.sh --include-legacy
```

### Release Validation

```bash
./scripts/release-check.sh
```

Or:

```bash
make release-check
```

## Example Event

```json
{
  "schema_version": "v2",
  "source_id": "manual-local",
  "payload": {
    "צ טנק": "צ'653",
    "חותמת זמן": "2026-02-08T10:00:00Z",
    "פלוגה": "כפיר",
    "דוח זיווד [חבל פריסה]": "חוסר"
  }
}
```

## Cloud Deployment Strategy

### Stage A (low-cost)

- Cloud Run (API + worker)
- Firestore-first read/write path
- Pub/Sub + Scheduler reconciliation
- Firebase Hosting for UI
- Secret Manager

### Stage B (upgrade gate)

Move read models to Cloud SQL when query complexity or latency thresholds are exceeded.

## Deploy Commands

One-command Stage A deployment:

```bash
./scripts/cloud/deploy-stage-a.sh <PROJECT_ID> <REGION> [SERVICE_NAME] [SERVICE_ACCOUNT_EMAIL]
```

Or with `make`:

```bash
make deploy-stage-a PROJECT_ID=<PROJECT_ID> REGION=<REGION> SERVICE_NAME=spearhead-api
```

Enable required APIs:

```bash
./scripts/cloud/enable-gcp-apis.sh <PROJECT_ID>
```

Deploy API to Cloud Run (build + deploy):

```bash
./scripts/cloud/deploy-api-cloudrun.sh <PROJECT_ID> <REGION> <SERVICE_NAME> [SERVICE_ACCOUNT_EMAIL]
```

If needed, set OAuth callback env before deploy:

```bash
export GOOGLE_OAUTH_REDIRECT_URI="https://<SERVICE_URL>/auth/google/callback"
```

Deploy reconciliation worker as Cloud Run Job:

```bash
./scripts/cloud/deploy-worker-cloudrun.sh <PROJECT_ID> <REGION> <JOB_NAME> <IMAGE_URI>
```

## Required Setup (You Need To Configure)

### Now

1. GCP billing-enabled project
2. Enabled APIs:
   - Cloud Run
   - Pub/Sub
   - Cloud Scheduler
   - Firestore
   - Secret Manager
   - Artifact Registry
   - Cloud Build
   - Firebase Hosting
   - Identity Toolkit / OAuth
3. OAuth consent screen + OAuth client IDs
4. Local tools:
   - `gcloud`
   - `docker`
   - `firebase-tools`
   - Node LTS
   - Python 3.11+

### Later (if/when upgrading query store)

1. Enable Cloud SQL Admin API
2. Provision Cloud SQL PostgreSQL
3. Add secrets + migration jobs

## Cost Note

Cloud SQL does not provide a permanent free tier for steady production usage.
For strict low-cost operation, keep Stage A first and upgrade by explicit trigger.
