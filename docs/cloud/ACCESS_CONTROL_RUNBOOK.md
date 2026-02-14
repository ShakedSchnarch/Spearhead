# Access Control Runbook (OAuth + App Authorization)

Last updated: 2026-02-14

This project has two independent access layers.  
Both must be updated when onboarding a new user.

## Layer A: Google OAuth Audience (Google Auth Platform)

Where:
- Google Cloud Console -> Google Auth Platform -> `Audience`

What to do:
1. Confirm `Publishing status`:
   - `Testing`: only `Test users` can sign in.
2. Add user email under `Test users`.
3. Save.

Notes:
- If a user is missing here, Google blocks login before callback with `access_denied: 403`.
- This is independent from app-level authorization.

## Layer B: App-Level Authorization (Secret Manager)

Where:
- Secret: `SPEARHEAD_AUTHORIZED_USERS`
- Format: JSON map `{ "email": "battalion|Kfir|Mahatz|Sufa|Palsam" }`

Recommended command (safe):

```bash
./scripts/cloud/manage-authorized-user.sh \
  --project spearhead-stg \
  --region europe-west1 \
  --service spearhead-api \
  --email user@example.com \
  --role battalion
```

Remove user:

```bash
./scripts/cloud/manage-authorized-user.sh \
  --project spearhead-stg \
  --region europe-west1 \
  --service spearhead-api \
  --email user@example.com \
  --remove
```

What the script does:
1. Reads current `SPEARHEAD_AUTHORIZED_USERS`.
2. Updates a single user entry.
3. Creates a new secret version.
4. Triggers a safe Cloud Run rollout (no secret clobbering).

## Safe Config Update Rules

For existing Cloud Run services, do not use destructive update flags.

- Non-secret env vars:
  - Use `--update-env-vars`
  - Avoid `--set-env-vars` unless you provide the full env map.
- Secret env vars:
  - Use `--update-secrets`
  - Avoid `--set-secrets` unless you provide the full secret env map.

## Quick Verification Checklist

1. Google layer:
   - User appears under `Audience -> Test users`.
2. App layer:
   - User appears in latest `SPEARHEAD_AUTHORIZED_USERS` secret payload.
3. Runtime:
   - Cloud Run latest revision is serving 100% traffic.
4. Login test:
   - Open `/spearhead/` in incognito and complete OAuth.

