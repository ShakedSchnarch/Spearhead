#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <GCP_PROJECT_ID>"
  exit 1
fi

PROJECT_ID="$1"

gcloud config set project "$PROJECT_ID"

gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  pubsub.googleapis.com \
  cloudscheduler.googleapis.com \
  firestore.googleapis.com \
  secretmanager.googleapis.com \
  identitytoolkit.googleapis.com \
  firebase.googleapis.com

echo "Enabled required Stage A APIs for project: $PROJECT_ID"
