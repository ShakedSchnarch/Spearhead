# Spearhead Runbook (v1 Responses-Only)

## 1. Start Services

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

## 4. Deprecated Endpoints Behavior

These endpoints intentionally return `410 Gone`:
- `GET /exports/platoon`
- `GET /exports/battalion`
- `POST /imports/platoon-loadout`
- `POST /imports/battalion-summary`

## 5. Testing

Run non-legacy suite:
```bash
./scripts/test.sh
```

Run v1 focused tests:
```bash
PYTHONPATH=src ./.venv/bin/pytest tests/test_v1_api.py -q
```

Release readiness check:

```bash
./scripts/release-check.sh
```

## 6. Production Checklist (Cloud)

- GCP billing active
- Cloud Run / PubSub / Scheduler / Firestore / Secret Manager enabled
- OAuth client configured
- Service accounts with least privilege
- Secrets loaded to Secret Manager (no plaintext in repo)
- API deployed with:
  - `./scripts/cloud/deploy-api-cloudrun.sh <PROJECT_ID> <REGION> <SERVICE_NAME> [SERVICE_ACCOUNT_EMAIL]`
- Optional reconciliation job deployed with:
  - `./scripts/cloud/deploy-worker-cloudrun.sh <PROJECT_ID> <REGION> <JOB_NAME> <IMAGE_URI>`
