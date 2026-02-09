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

Create these optional secrets in Secret Manager:
- `SPEARHEAD_API_TOKEN`
- `SPEARHEAD_OAUTH_CLIENT_ID`
- `SPEARHEAD_OAUTH_CLIENT_SECRET`

If they exist, deployment script maps them automatically to Cloud Run env vars.

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
- Move to Cloud SQL only after explicit performance/complexity triggers.
