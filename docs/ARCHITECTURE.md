# Spearhead Architecture (Release Runtime)

## Scope

Spearhead runtime is responses-only:
- ingest form response events
- normalize and store
- build/read query-oriented snapshots
- expose `/v1` API for dashboard/UI

Legacy endpoints/modules are optional and disabled by default.

## Runtime Layers

1. **API Layer**
   - `src/spearhead/api/main.py`
   - `src/spearhead/api/routers/v1.py`
   - `src/spearhead/api/routers/system.py`

2. **Application Layer (v1)**
   - `src/spearhead/v1/parser.py`
   - `src/spearhead/v1/service.py`
   - `src/spearhead/v1/worker.py`
   - `src/spearhead/v1/reconcile.py`

3. **Persistence Layer**
   - `src/spearhead/v1/store.py`
   - `src/spearhead/data/storage.py`

4. **Frontend**
   - `frontend-app/src/App.jsx`
   - `frontend-app/src/components/SimpleLogin.jsx`
   - `frontend-app/src/components/DashboardContent.jsx`
   - `frontend-app/src/api/client.js`

## Folder Contract

- `src/spearhead/v1`: active business/runtime logic.
- `src/spearhead/api`: HTTP wiring and auth/session boundaries.
- `frontend-app/src`: minimal UI runtime.
- `scripts`: active local/release scripts.
- `scripts/cloud`: deployment scripts.
- `scripts/legacy`: historical scripts kept for reference only.
- `docs/archive`: historical documents and samples.

## Runtime Entry Points

- Local one-click run:
  - `./scripts/dev-one-click.sh`
- Local direct run:
  - `./scripts/run-local.sh`
- Python CLI:
  - `spearhead serve --reload`
  - `spearhead reconcile`

## Deployment Entry Points

- Stage A one-command:
  - `./scripts/cloud/deploy-stage-a.sh <PROJECT_ID> <REGION> [SERVICE_NAME] [SERVICE_ACCOUNT_EMAIL]`
- API deploy:
  - `./scripts/cloud/deploy-api-cloudrun.sh ...`
- Worker deploy:
  - `./scripts/cloud/deploy-worker-cloudrun.sh ...`

## Guardrails

- Keep `APP__ENABLE_LEGACY_ROUTES=false` in production unless migration requires otherwise.
- Do not add heavy business logic to frontend; calculations stay in backend `v1`.
- Keep API contract versioned under `/v1`.
