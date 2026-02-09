#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <PROJECT_ID> <REGION> [SERVICE_NAME] [SERVICE_ACCOUNT_EMAIL]"
  exit 1
fi

PROJECT_ID="$1"
REGION="$2"
SERVICE_NAME="${3:-spearhead-api}"
SERVICE_ACCOUNT_EMAIL="${4:-}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

"$ROOT/scripts/cloud/enable-gcp-apis.sh" "$PROJECT_ID"
"$ROOT/scripts/cloud/deploy-api-cloudrun.sh" "$PROJECT_ID" "$REGION" "$SERVICE_NAME" "$SERVICE_ACCOUNT_EMAIL"

echo
echo "Stage A deployment completed."
echo "If Firestore is not created yet, run:"
echo "  gcloud firestore databases create --database=\"(default)\" --location=${REGION} --type=firestore-native"
