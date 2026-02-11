# Environment Setup Checklist

## 1) Local development (`.env`)

Required now:
- `SECURITY__API_TOKEN`
- `SECURITY__AUTHORIZED_USERS` (JSON email -> role map). If empty, all users are allowed (dev-only).
- `GOOGLE__OAUTH_CLIENT_ID`
- `GOOGLE__OAUTH_CLIENT_SECRET`
- `GOOGLE__OAUTH_REDIRECT_URI` (local callback)
- `STORAGE__BACKEND=sqlite`
- `PATHS__DB_PATH=./data/ironview.db` (or your active local DB file)

Optional now:
- `GOOGLE__SERVICE_ACCOUNT_FILE`
- `GOOGLE__FILE_IDS__FORM_RESPONSES`
- `VITE_GOOGLE_OAUTH_URL` (frontend direct OAuth URL; usually keep empty)
- `VITE_ALLOW_GUEST_LOGIN` (`true` only for local troubleshooting)
- all `AI__*` fields (phase disabled)

## 2) Cloud Run deployment

Required:
- `STORAGE__BACKEND=firestore`
- `STORAGE__FIRESTORE_PROJECT_ID=<PROJECT_ID>`
- `SECURITY__REQUIRE_AUTH_ON_QUERIES=true`
- `GOOGLE__OAUTH_REDIRECT_URI=https://<RUN_URL>/auth/google/callback`
- Secret Manager values:
  - `SPEARHEAD_API_TOKEN`
  - `SPEARHEAD_OAUTH_CLIENT_ID`
  - `SPEARHEAD_OAUTH_CLIENT_SECRET`
  - `SPEARHEAD_AUTHORIZED_USERS` (JSON map, required when auth is enforced)

## 3) Fast fetch commands (gcloud CLI)

```bash
PROJECT_ID="$(gcloud config get-value project)"
REGION="europe-west1"
SERVICE_NAME="spearhead-api"

gcloud run services describe "$SERVICE_NAME" \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --format="value(status.url)"

gcloud secrets list --project "$PROJECT_ID" --format="value(name)"

gcloud firestore databases list --project "$PROJECT_ID" \
  --format="table(name,locationId,type)"
```

## 4) Security note

- Never keep production secrets inside git-tracked files.
- Rotate any exposed key/token immediately and keep runtime secrets in Secret Manager.
- If `SECURITY__REQUIRE_AUTH_ON_QUERIES=true` and `SECURITY__AUTHORIZED_USERS` is empty, OAuth login is blocked by design.
