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
- Env checklist: `docs/cloud/ENV_SETUP_CHECKLIST.md`
- Active working plan: `docs/cloud/WORKING_PLAN.md`
- Master tasks tracker: `docs/PROJECT_TASKS.md`
- Company data sources: `docs/cloud/DATA_SOURCES.md`
- Remaining tasks status: `docs/cloud/REMAINING_TASKS_STATUS.md`
- Forms contract: `docs/forms/FORMS_CONTRACT.md`
- Forms track tooling: `docs/forms/README.md`
- Historical plans/samples: `docs/archive/`

## Forms Artifacts

```bash
python3 scripts/forms/generate-kfir-form-blueprint.py
python3 scripts/forms/generate-google-form-apps-script.py \
  --standards config/operational_standards.yaml
```

Generated outputs:
- `docs/forms/kfir_company_form_blueprint.json`
- `docs/forms/kfir_google_form_apps_script.gs`

Operational standards source of truth:
- `config/operational_standards.yaml`

AI modes:
- Offline deterministic mode (free/default): `AI__ENABLED=false`
- Remote provider mode (optional): set `AI__ENABLED=true`, `AI__PROVIDER=http`, `AI__BASE_URL`, `AI__API_KEY`

## Active API (v1)

- `POST /v1/ingestion/forms/events`
- `POST /v1/ingestion/forms/company-assets`
- `GET /v1/metrics/overview?week=YYYY-Www`
- `GET /v1/metrics/platoons/{platoon}?week=YYYY-Www`
- `GET /v1/metrics/tanks?platoon=...&week=...`
- `GET /v1/queries/gaps?week=...&platoon=...&group_by=item|tank|family`
- `GET /v1/queries/trends?metric=reports|total_gaps|gap_rate|distinct_tanks&window_weeks=...&platoon=...`
- `GET /v1/queries/search?q=...&week=...&platoon=...`
- `GET /v1/metadata/weeks?platoon=...`
- `GET /v1/views/battalion?week=...`
- `GET /v1/views/battalion/ai-analysis?week=...`
- `GET /v1/views/companies/{company}?week=...`
- `GET /v1/views/companies/{company}/tanks?week=...`
- `GET /v1/views/companies/{company}/sections/{section}/tanks?week=...`
- `GET /v1/views/companies/{company}/tanks/{tank_id}/inventory?week=...`
- `GET /v1/views/companies/{company}/assets?week=...`

Command views now include:
- readiness scores (tank/section/company)
- critical gap counts and top critical items

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
./scripts/bootstrap-dev-env.sh
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
- auth is disabled by default for local runs (`LOCAL_DEV_ENFORCE_AUTH=true` to enforce auth)

### Managed local server (background)

```bash
./scripts/local-dev.sh start
./scripts/local-dev.sh status
./scripts/local-dev.sh logs
./scripts/local-dev.sh stop
```

### Backend

```bash
./scripts/bootstrap-dev-env.sh
./.venv/bin/python -m uvicorn spearhead.api.main:app --reload --port 8000
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

- Cloud Run (single API service serving backend + built frontend)
- Firestore-backed v1 store (`STORAGE__BACKEND=firestore`)
- Optional Cloud Run Job for reconciliation/sync
- Secret Manager for API/OAuth secrets
- `min-instances=0` for lowest idle cost

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

Bootstrap first real data from Kfir weekly matrix sheet:

```bash
PYTHONPATH=src ./scripts/cloud/ingest-matrix-sheet.py \
  --sheet-id 13P9dOUSIc5IiBrdPWSuTZ2LKnWO56aDU1lJ7okGENqw \
  --company Kfir \
  --api-base-url https://<SERVICE_URL> \
  --api-token <SPEARHEAD_API_TOKEN> \
  --year 2026
```

Ingest multiple company matrix sources from registry:

```bash
PYTHONPATH=src ./scripts/cloud/ingest-company-sources.py \
  --api-base-url https://<SERVICE_URL> \
  --api-token <SPEARHEAD_API_TOKEN> \
  --year 2026
```

## Required Setup (You Need To Configure)

### Now

1. GCP billing-enabled project
2. Enabled APIs:
   - Cloud Run
   - Firestore
   - Secret Manager
   - Artifact Registry
   - Cloud Build
   - Identity Toolkit / OAuth
   - (Optional) Pub/Sub + Cloud Scheduler for automated reconciliation triggers
3. OAuth consent screen + OAuth client IDs
4. Local tools:
   - `gcloud`
   - `docker`
   - Node LTS
   - Python 3.11+

### Later (if/when upgrading query store)

1. Enable Cloud SQL Admin API
2. Provision Cloud SQL PostgreSQL
3. Add secrets + migration jobs

## Cost Note

Cloud SQL does not provide a permanent free tier for steady production usage.
For strict low-cost operation, keep Stage A first and upgrade by explicit trigger.
