#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Usage: $0 <GCP_PROJECT_ID> <REGION> <SERVICE_NAME> [SERVICE_ACCOUNT_EMAIL]"
  exit 1
fi

PROJECT_ID="$1"
REGION="$2"
SERVICE_NAME="$3"
SERVICE_ACCOUNT_EMAIL="${4:-}"
REPO_NAME="spearhead"
IMAGE_TAG="${IMAGE_TAG:-$(date +%Y%m%d%H%M%S)}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/spearhead-api:${IMAGE_TAG}"

gcloud config set project "$PROJECT_ID"

gcloud artifacts repositories create "$REPO_NAME" \
  --repository-format=docker \
  --location="$REGION" \
  --description="Spearhead container images" \
  2>/dev/null || true

gcloud builds submit --tag "$IMAGE" .

DEPLOY_ARGS=(
  gcloud run deploy "$SERVICE_NAME"
  --image "$IMAGE"
  --region "$REGION"
  --platform managed
  --allow-unauthenticated
  --min-instances 0
  --max-instances 2
  --port 8080
  --set-env-vars "PYTHONPATH=src,APP__ENABLE_LEGACY_ROUTES=false"
)

if [[ -n "$SERVICE_ACCOUNT_EMAIL" ]]; then
  DEPLOY_ARGS+=(--service-account "$SERVICE_ACCOUNT_EMAIL")
fi

if [[ -n "${GOOGLE_OAUTH_REDIRECT_URI:-}" ]]; then
  DEPLOY_ARGS+=(--set-env-vars "GOOGLE__OAUTH_REDIRECT_URI=${GOOGLE_OAUTH_REDIRECT_URI}")
fi

for SECRET_NAME in SPEARHEAD_API_TOKEN SPEARHEAD_OAUTH_CLIENT_ID SPEARHEAD_OAUTH_CLIENT_SECRET; do
  if gcloud secrets describe "$SECRET_NAME" >/dev/null 2>&1; then
    case "$SECRET_NAME" in
      SPEARHEAD_API_TOKEN)
        DEPLOY_ARGS+=(--set-secrets "SECURITY__API_TOKEN=${SECRET_NAME}:latest")
        ;;
      SPEARHEAD_OAUTH_CLIENT_ID)
        DEPLOY_ARGS+=(--set-secrets "GOOGLE__OAUTH_CLIENT_ID=${SECRET_NAME}:latest")
        ;;
      SPEARHEAD_OAUTH_CLIENT_SECRET)
        DEPLOY_ARGS+=(--set-secrets "GOOGLE__OAUTH_CLIENT_SECRET=${SECRET_NAME}:latest")
        ;;
    esac
  fi
done

"${DEPLOY_ARGS[@]}"

echo "API deployed: $SERVICE_NAME"
echo "Image: $IMAGE"
