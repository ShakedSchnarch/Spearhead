# Focused Redesign + GCP Rollout Roadmap

This roadmap is optimized for a small team and a few weeks of execution.
It assumes the current Spearhead codebase and keeps architecture intentionally minimal.

## Target Architecture (Stage A)

1. Cloud Run service:
   - Hosts FastAPI API and built frontend (`/spearhead`)
2. Firestore:
   - Primary runtime store (`STORAGE__BACKEND=firestore`)
3. Secret Manager:
   - API token and OAuth client secrets
4. Optional Cloud Run Job:
   - Reconciliation/sync worker, manually triggered first

## Core Decisions (Now Locked)

1. Keep one deployable service in Stage A (no separate frontend hosting).
2. Keep Google OAuth + session-based app auth.
3. Enforce auth on query/view routes in production.
4. Use fixed operational sections:
   - Armament
   - Logistics
   - Communications
5. Use config-driven family-to-section mapping (no hard-coded UI rules).

## Delivery Phases

## Phase 1 - Runtime Foundations

1. Deploy API to Cloud Run with Firestore backend:
   - `./scripts/cloud/deploy-stage-a.sh <PROJECT_ID> <REGION> <SERVICE_NAME>`
2. Confirm env/runtime:
   - `STORAGE__BACKEND=firestore`
   - `SECURITY__REQUIRE_AUTH_ON_QUERIES=true`
3. Verify:
   - `/health` returns 200
   - `/v1/metadata/weeks` returns 401 before auth

## Phase 2 - Auth + Access Control

1. Configure OAuth consent/client in Google Cloud.
2. Set callback:
   - `https://<SERVICE_URL>/auth/google/callback`
3. Load secrets:
   - `SPEARHEAD_OAUTH_CLIENT_ID`
   - `SPEARHEAD_OAUTH_CLIENT_SECRET`
4. Update allow-list:
   - `SECURITY__AUTHORIZED_USERS` via env/config

## Phase 3 - Data Flow

1. Use ingestion endpoint for initial validation:
   - `POST /v1/ingestion/forms/events`
2. Validate command views:
   - `GET /v1/views/battalion`
   - `GET /v1/views/companies/{company}`
   - `GET /v1/views/companies/{company}/sections/{section}/tanks`
3. Add worker job only after API flow is stable.

## Phase 4 - Meeting Workflow Adoption

1. Battalion commanders use battalion view for cross-company comparison.
2. Drill down to company view during meeting discussion.
3. Focus on section-level gaps and week-over-week deltas.

## Phase 5 - Hardening

1. Rotate OAuth/API secrets.
2. Restrict authorized users list.
3. Set monitoring/alerts (5xx and auth failures).
4. Add scheduled reconciliation trigger only when needed.

## Upgrade Trigger (Stage B)

Move read models to Cloud SQL only when one or more are true:

1. Query latency is consistently high under real meeting load.
2. Firestore query shape becomes operationally complex.
3. Reporting requirements need stronger relational joins.
