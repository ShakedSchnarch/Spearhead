#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 4 ]]; then
  echo "Usage: $0 <GCP_PROJECT_ID> <REGION> <JOB_NAME> <IMAGE_URI>"
  exit 1
fi

PROJECT_ID="$1"
REGION="$2"
JOB_NAME="$3"
IMAGE="$4"

gcloud config set project "$PROJECT_ID"

gcloud run jobs deploy "$JOB_NAME" \
  --image "$IMAGE" \
  --region "$REGION" \
  --tasks 1 \
  --max-retries 1 \
  --set-env-vars "PYTHONPATH=src,APP__ENABLE_LEGACY_ROUTES=false,STORAGE__BACKEND=firestore,STORAGE__FIRESTORE_PROJECT_ID=${PROJECT_ID}" \
  --command python \
  --args=-m \
  --args=spearhead.v1.reconcile

echo "Worker job deployed: $JOB_NAME"
echo "Run manually with: gcloud run jobs execute $JOB_NAME --region $REGION"
