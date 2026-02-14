# Stage A Cloud Setup (Google-First, Low-Cost)

## 1. Prerequisites

- Billing-enabled GCP project
- `gcloud` CLI authenticated
- `docker` installed (for local builds if needed)

## 2. Enable APIs

```bash
./scripts/cloud/enable-gcp-apis.sh <PROJECT_ID>
```

Shortcut (enable + build + deploy API):

```bash
./scripts/cloud/deploy-stage-a.sh <PROJECT_ID> <REGION> [SERVICE_NAME] [SERVICE_ACCOUNT_EMAIL]
```

## 3. Create Firestore (one-time)

```bash
gcloud config set project <PROJECT_ID>
gcloud firestore databases create --database="(default)" --location=<REGION> --type=firestore-native
```

## 4. Store secrets

Create these secrets in Secret Manager:
- `SPEARHEAD_API_TOKEN`
- `SPEARHEAD_OAUTH_CLIENT_ID`
- `SPEARHEAD_OAUTH_CLIENT_SECRET`
- `SPEARHEAD_AUTHORIZED_USERS` (JSON map: `{"email":"battalion|Kfir|Mahatz|Sufa"}`)

`SPEARHEAD_API_TOKEN` is strongly recommended so ingestion/admin operations require explicit auth.
Deployment script maps existing secrets automatically to Cloud Run env vars.
If `SECURITY__REQUIRE_AUTH_ON_QUERIES=true` and `SPEARHEAD_AUTHORIZED_USERS` is missing/empty, OAuth login is blocked by design.

## 5. Deploy API (build + deploy)

Optional (recommended) before deploy:

```bash
export GOOGLE_OAUTH_REDIRECT_URI="https://<SERVICE_URL>/auth/google/callback"
```

```bash
./scripts/cloud/deploy-api-cloudrun.sh <PROJECT_ID> <REGION> <SERVICE_NAME> [SERVICE_ACCOUNT_EMAIL]
```

The script:
- builds container from `Dockerfile`
- pushes image to Artifact Registry
- deploys Cloud Run with responses-only runtime defaults
- configures Firestore backend (`STORAGE__BACKEND=firestore`)
- enables query auth requirement (`SECURITY__REQUIRE_AUTH_ON_QUERIES=true`)

## 6. Deploy worker reconciliation job (optional)

Use the image URI printed by API deployment output.

```bash
./scripts/cloud/deploy-worker-cloudrun.sh <PROJECT_ID> <REGION> <JOB_NAME> <IMAGE_URI>
```

Run it manually:

```bash
gcloud run jobs execute <JOB_NAME> --region <REGION>
```

## 7. Configure OAuth callback

Set OAuth redirect URI to:

`https://<SERVICE_URL>/auth/google/callback`

And set in runtime env/secrets:
- `GOOGLE__OAUTH_CLIENT_ID`
- `GOOGLE__OAUTH_CLIENT_SECRET`
- `GOOGLE__OAUTH_REDIRECT_URI`

## 8. Notes

- Stage A cost profile stays low with `min-instances=0`.
- Cold starts are expected.
- Cloud Run remains publicly reachable at network level, but data routes are guarded by app auth/session checks.
- Move to Cloud SQL only after explicit performance/complexity triggers.

## 9. First Data Load (Kfir Matrix Workbook)

After first deploy + auth, load initial real data so dashboard is not empty:

```bash
PROJECT_ID="$(gcloud config get-value project)"
REGION="europe-west1"
SERVICE_NAME="spearhead-api"
SERVICE_URL="$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format='value(status.url)')"
API_TOKEN="$(gcloud secrets versions access latest --secret=SPEARHEAD_API_TOKEN --project "$PROJECT_ID")"

PYTHONPATH=src ./scripts/cloud/ingest-matrix-sheet.py \
  --sheet-id 13P9dOUSIc5IiBrdPWSuTZ2LKnWO56aDU1lJ7okGENqw \
  --company Kfir \
  --api-base-url "$SERVICE_URL" \
  --api-token "$API_TOKEN" \
  --year 2026
```

For battalion expansion (Kfir+Mahatz+Sufa) using registry:

```bash
PYTHONPATH=src ./scripts/cloud/ingest-company-sources.py \
  --api-base-url "$SERVICE_URL" \
  --api-token "$API_TOKEN" \
  --year 2026
```
