# Spearhead Runbook (v1 Responses-Only)

## 1. Start Services

Prepare env once:

```bash
./scripts/bootstrap-dev-env.sh
```

Single terminal startup:

```bash
./scripts/dev-one-click.sh
```

Equivalent:

```bash
./scripts/run-local.sh
```

Open:

- `http://127.0.0.1:8000/spearhead/`

## 2. Health Checks

- `GET /health`
- `GET /v1/metadata/weeks`

## 3. Smoke Test (Ingestion -> Query)

1. Ingest one event:
```bash
curl -X POST http://127.0.0.1:8000/v1/ingestion/forms/events \
  -H 'Content-Type: application/json' \
  -d '{
    "schema_version":"v2",
    "source_id":"manual-smoke",
    "payload":{
      "צ טנק":"צ\'653",
      "חותמת זמן":"2026-02-08T10:00:00Z",
      "פלוגה":"כפיר",
      "דוח זיווד [חבל פריסה]":"חוסר"
    }
  }'
```

2. Query overview:
```bash
curl "http://127.0.0.1:8000/v1/metrics/overview"
```

3. Query gaps:
```bash
curl "http://127.0.0.1:8000/v1/queries/gaps?group_by=item"
```

4. Query command views:
```bash
curl "http://127.0.0.1:8000/v1/views/battalion"
curl "http://127.0.0.1:8000/v1/views/companies/Kfir"
curl "http://127.0.0.1:8000/v1/views/companies/Kfir/tanks"
curl "http://127.0.0.1:8000/v1/views/companies/Kfir/sections/Logistics/tanks"
```

### Readiness and critical gaps

- Readiness score is calculated per section and per tank from checked items vs gaps.
- Critical gap penalty is applied when a gap belongs to configured critical items.
- Current critical baseline (Kfir) is derived from red-marked items in `שבוע 7`.

## 4. Bootstrap Real Data From Weekly Matrix Sheet (Cloud)

The Kfir workbook format is matrix-based (`שבוע X` tabs, tanks as columns).
Use the helper script to convert it into v1 response events and ingest to Cloud Run.

1. Set Cloud context and pull runtime values:
```bash
gcloud config set project <PROJECT_ID>
PROJECT_ID="$(gcloud config get-value project)"
REGION="europe-west1"
SERVICE_NAME="spearhead-api"
SERVICE_URL="$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format='value(status.url)')"
API_TOKEN="$(gcloud secrets versions access latest --secret=SPEARHEAD_API_TOKEN --project "$PROJECT_ID")"
```

2. Dry-run parse from Google Sheet ID:
```bash
PYTHONPATH=src ./scripts/cloud/ingest-matrix-sheet.py \
  --sheet-id 13P9dOUSIc5IiBrdPWSuTZ2LKnWO56aDU1lJ7okGENqw \
  --company Kfir \
  --api-base-url "$SERVICE_URL" \
  --api-token "$API_TOKEN" \
  --year 2026 \
  --dry-run
```

3. Ingest to cloud:
```bash
PYTHONPATH=src ./scripts/cloud/ingest-matrix-sheet.py \
  --sheet-id 13P9dOUSIc5IiBrdPWSuTZ2LKnWO56aDU1lJ7okGENqw \
  --company Kfir \
  --api-base-url "$SERVICE_URL" \
  --api-token "$API_TOKEN" \
  --year 2026
```

4. Verify weeks and battalion view:
```bash
curl -H "X-API-Key: $API_TOKEN" "$SERVICE_URL/v1/metadata/weeks"
curl -H "X-API-Key: $API_TOKEN" "$SERVICE_URL/v1/views/battalion"
```

## 5. Deprecated Endpoints Behavior

These endpoints intentionally return `410 Gone`:
- `GET /exports/platoon`
- `GET /exports/battalion`
- `POST /imports/platoon-loadout`
- `POST /imports/battalion-summary`

## 6. Testing

Run non-legacy suite:
```bash
./scripts/test.sh
```

Run v1 focused tests:
```bash
PYTHONPATH=src ./.venv/bin/python -m pytest tests/test_v1_api.py -q
```

Release readiness check:

```bash
./scripts/release-check.sh
```

## 7. Production Checklist (Cloud)

- GCP billing active
- Cloud Run / PubSub / Scheduler / Firestore / Secret Manager enabled
- OAuth client configured
- Service accounts with least privilege
- Secrets loaded to Secret Manager (no plaintext in repo)
- API deployed with:
  - `./scripts/cloud/deploy-api-cloudrun.sh <PROJECT_ID> <REGION> <SERVICE_NAME> [SERVICE_ACCOUNT_EMAIL]`
- Optional reconciliation job deployed with:
  - `./scripts/cloud/deploy-worker-cloudrun.sh <PROJECT_ID> <REGION> <JOB_NAME> <IMAGE_URI>`
