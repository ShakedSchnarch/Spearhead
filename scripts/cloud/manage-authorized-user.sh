#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  manage-authorized-user.sh --email <EMAIL> [--role <ROLE>] [--remove] [--dry-run]
                           [--project <PROJECT_ID>] [--region <REGION>] [--service <SERVICE_NAME>]
                           [--secret <SECRET_NAME>]

Defaults:
  --role battalion
  --project from current gcloud config
  --region europe-west1
  --service spearhead-api
  --secret SPEARHEAD_AUTHORIZED_USERS

Examples:
  ./scripts/cloud/manage-authorized-user.sh --email commander@example.com --role battalion
  ./scripts/cloud/manage-authorized-user.sh --email user@example.com --role Kfir
  ./scripts/cloud/manage-authorized-user.sh --email user@example.com --remove
EOF
}

PROJECT="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || true)}"
REGION="${REGION:-europe-west1}"
SERVICE="${SERVICE_NAME:-spearhead-api}"
SECRET="${AUTHORIZED_USERS_SECRET:-SPEARHEAD_AUTHORIZED_USERS}"
EMAIL=""
ROLE="battalion"
REMOVE="false"
DRY_RUN="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --email)
      EMAIL="${2:-}"
      shift 2
      ;;
    --role)
      ROLE="${2:-}"
      shift 2
      ;;
    --remove)
      REMOVE="true"
      shift
      ;;
    --project)
      PROJECT="${2:-}"
      shift 2
      ;;
    --region)
      REGION="${2:-}"
      shift 2
      ;;
    --service)
      SERVICE="${2:-}"
      shift 2
      ;;
    --secret)
      SECRET="${2:-}"
      shift 2
      ;;
    --dry-run)
      DRY_RUN="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$PROJECT" ]]; then
  echo "Missing project. Set --project or run 'gcloud config set project <PROJECT_ID>'." >&2
  exit 1
fi

if [[ -z "$EMAIL" ]]; then
  echo "Missing required flag: --email" >&2
  usage
  exit 1
fi

TMP_CURRENT="$(mktemp)"
TMP_NEW="$(mktemp)"
cleanup() {
  rm -f "$TMP_CURRENT" "$TMP_NEW"
}
trap cleanup EXIT

if ! gcloud secrets versions access latest --secret="$SECRET" --project "$PROJECT" > "$TMP_CURRENT" 2>/dev/null; then
  echo "{}" > "$TMP_CURRENT"
fi

python3 - <<'PY' "$TMP_CURRENT" "$TMP_NEW" "$EMAIL" "$ROLE" "$REMOVE"
import json
import sys

src, dst, email, role, remove = sys.argv[1:6]
email = (email or "").strip().lower()
role = (role or "").strip()
remove = (remove or "").strip().lower() == "true"

if "@" not in email:
    raise SystemExit(f"Invalid email: {email}")

allowed_roles = {"battalion", "Kfir", "Mahatz", "Sufa", "Palsam"}
if not remove and role not in allowed_roles:
    raise SystemExit(
        f"Invalid role: {role}. Allowed: {', '.join(sorted(allowed_roles))}"
    )

try:
    with open(src, "r", encoding="utf-8") as f:
        payload = json.load(f) or {}
except Exception:
    payload = {}

if not isinstance(payload, dict):
    raise SystemExit("Secret payload must be a JSON object mapping email -> role")

normalized = {
    str(k).strip().lower(): str(v).strip()
    for k, v in payload.items()
    if str(k).strip()
}

if remove:
    normalized.pop(email, None)
else:
    normalized[email] = role

with open(dst, "w", encoding="utf-8") as f:
    json.dump(normalized, f, ensure_ascii=False, separators=(",", ":"))

print(json.dumps(normalized, ensure_ascii=False, indent=2))
PY

echo
echo "Planned authorized-users payload:"
cat "$TMP_NEW"
echo

if [[ "$DRY_RUN" == "true" ]]; then
  echo "[dry-run] No secret version added, no rollout executed."
  exit 0
fi

gcloud secrets versions add "$SECRET" \
  --project "$PROJECT" \
  --data-file "$TMP_NEW" >/dev/null

# Force a fresh revision so running instances reload latest secret value.
gcloud run services update "$SERVICE" \
  --project "$PROJECT" \
  --region "$REGION" \
  --update-secrets "SECURITY__AUTHORIZED_USERS=${SECRET}:latest" \
  --update-env-vars "AUTHZ_ROLLOUT_NONCE=$(date +%s)" >/dev/null

echo "Done."
echo "Project: $PROJECT"
echo "Service: $SERVICE"
echo "Secret:  $SECRET"
echo "Updated user: $EMAIL"
if [[ "$REMOVE" == "true" ]]; then
  echo "Action: removed"
else
  echo "Role: $ROLE"
fi

