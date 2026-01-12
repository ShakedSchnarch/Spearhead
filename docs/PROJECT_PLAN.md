# IronView – Project Plan and Standards

## Vision and Scope
- Local-first operational dashboard for the S3/CO to ingest weekly company/battalion readiness spreadsheets and serve web reports.
- Support two intake modes: local file upload (default/offline) and optional Google Sheets pull (with cached copies and explicit credentials).
- Deterministic analytics first (inventory/status deltas, gaps, trends), with an opt-in AI layer later for anomaly detection and long-range insights.

## Current Stage (Completed)
- Backend ingestion/query/AI scaffold: adapters for platoon loadout, battalion summary, and form responses; SQLite with idempotent imports; deterministic queries (totals/gaps/by-platoon/delta/variance/form-status); AI stub; tests green.
- API + frontend: FastAPI with CORS, static serve of built React/Vite dashboard at `/app` (filters/sort/trends), optional auth guardrails; Google Sheets sync with cache/etag/retry + status.
- Analytics/exports: dynamic tank counts from form responses, zivud gaps, ammo per-tank averages, means gaps, commander capture; Excel exports (platoon/battalion).
- Scripts: `dev-api.sh`, `dev-ui.sh`, `build-ui.sh`, `test.sh`, `clean-db.sh`, `seed-and-export.sh`, `sync-and-export.sh` (sync from Sheets if enabled, else samples → export).

## Execution Plan (refresh for structured rollout)
Goal: tighten layering, standardize frontend data flow, finish OAuth/Sheets integration, and ship a predictable release-ready stack. Each phase ends with validation (pytest + UI build) and doc updates.

### Phase 0 — Baseline & guardrails (Completed)
- [x] Lock repository conventions: paths, env, scripts, lint/format, DB location. Check `.gitignore`.
- [x] Confirm settings defaults: Google disabled, Auth optional.
- [x] Verified generated artifacts policy.
- [x] DoD Met: `pytest` green, `npm run build` passes, scripts functional.

### Phase 1 — Structure & separation (backend + frontend)
- Backend: enforce layering within repo modules: `data` (adapters/storage/import), `services` (analytics/queries), `sync` (providers/service), `api` (routers/middleware). `SyncService` only depends on provider + import; API should not reach adapters directly. OAuth session store behind an interface; sync status schema consistent.
- Frontend: finalize layout (`components/`, `hooks/`, `api/`, `types/`, optional `styles/`); all network via `api/client` + React Query keys; single persisted state (apiBase/token/oauthSession/platoon/week/viewMode/topN). Remove legacy `api.js`/CSS remnants; Mantine/RTL defaults kept.
- Logging/metrics standard drafted (request_id, auth_mode, sheet_id, platoon) for later phases.
- Deliverables: component map + data flow diagram; lint/build clean.

### Phase 2 — Auth/OAuth + Google Sheets hardening
- Server: add refresh-token handling and expiry cleanup to OAuth store; optional persistence hook (in-memory default). Improve `/sync/status` with `auth_mode`/source and clearer 401/403/429 paths with cache fallback. Refresh-token policy documented (TTL, storage, PII guardrails).
- Client: login overlay shows OAuth readiness; store `session` separately from API token; send `X-OAuth-Session`; handle expiry banner and manual fallback upload. Surface sync source/auth_mode/etag in UI.
- Error semantics: invalid/expired session → 401 with clear detail; exports/sync unauthenticated → 401/403; rate-limit messages (429) bubbled to UI.
- Tests: unit for OAuth store TTL/refresh; sync provider fallbacks with user token; API tests for headers/query params; UI banner on 401/expired session.

### Phase 3 — Data shaping, queries, and exports
- Verify coverage defaults (latest week) across summary/coverage/tabular endpoints; align battalion vs. platoon responses and error codes.
- Exports: enforce filters (week/platoon), user-token auth, and descriptive errors (404/422 with detail). Add smoke for HQ/unknown platoons and dynamic filenames.
- Analytics: validate anomaly thresholds and report tokens; keep schema snapshots lean (retention cap/cleanup documented).
- Tests: expand `test_sync`, `test_queries`, export smoke (platoon/battalion), error-path tests for missing filters/auth.

### Phase 4 — Dashboard UX & interactions
- Consolidated filter bar (mode/week/platoon/section/topN) + localStorage; consistent empty/error states; RTL-ready tables/charts with tooltips/legends.
- Navigation: battalion/platoon cards with logos; header with user/session/source info; action bar (sync/refresh/export/upload) unified.
- Reduce duplication: shared KPI strip, table components, chart wrappers; loading/skeleton states for React Query.
- UX standards: banner/notification tone mapping; loading/empty/error patterns; maintain Mantine theme RTL; avoid ad-hoc buttons/styles.

### Phase 5 — Observability & operations
- Structured logging (request_id, auth_mode, sheet id, platoon) and sync metrics; optional file-rotation config. Clarify log destination and retention.
- Scripts: one-click dev (`dev-api.sh`, `dev-ui.sh`), reset, test-build-run. Add CI target or doc for local pre-commit (lint + pytest + UI build). Keep `.env` defaults safe (Google off, AI off).
- Operational runbook pointer: how to start services, view logs, clean generated data, and smoke-test auth/sync.

### Phase 6 — Docs, readiness, release
- Update README + this plan with the new architecture, OAuth flow, sync header usage, folder layout, and cleanup commands.
- Final QA: `scripts/clean-db.sh` → sample import/sync → exports → UI smoke (battalion/platoon) → pytest → `npm run build`. Verify error semantics (exports without filters/auth) and sync status shows `auth_mode`.

## Release Notes (Internal)
- OAuth callback now persists a short-lived session (in-memory) with access/refresh tokens and state; `/sync/google` consumes user tokens via `X-OAuth-Session` when present and falls back to service account/API key with `auth_mode` tracked.
- Phase 2: Config-driven parsing (fields.yaml), header normalization with wildcards, schema snapshots, validation, and unmapped logging.
- Phase 3: Battalion/Platoon view modes; `/queries/forms/summary`; frontend toggle + KPIs and sync source/etag.
- Phase 4: UX polish (Hebrew UI, RTL, navigation anchors, empty states, auth banners).
- Phase 5: Auth wired end-to-end (token/basic, UI token field); auth smoke documented.
- Phase 7: QA pass with local fixtures; reports emitted to `reports/`; pytest green.

## Architecture (Current)
- Data: Adapters (xlsx), DTOs, SQLite storage, ImportService (hash idempotency), Google Sync provider/service, QueryService (deterministic).
- API: FastAPI app factory; imports, queries, sync/google, health; static serve of `frontend-app/dist` at `/app` if present.
- Frontend: `frontend-app/` (Vite React with Mantine for UI, Chart.js lazily loaded for charts) consuming API; builds to dist.
- Tests: unit/integration across adapters, import service, queries, API, sync.

## Engineering Standards & Context
- Code in English; status tokens configurable in `config.py`.
- No legacy renderer: removed Jinja dashboard and run_iron_view.sh; React/Vite is the UI path.
- Offline-first: assets local; CORS on; API serves built UI.
- Google Sheets sync is now a first-class feature (enabled via config).
- AI to be reintroduced with a new, clean design (old file removed).

## Target Architecture (layered)
- Data layer (`src/iron_view/data`):
  - Adapters: `PlatoonLoadoutAdapter`, `BattalionSummaryAdapter`, `FormResponsesAdapter` to parse the supplied Excel formats (multi-row headers, Hebrew labels, status strings).
  - DTOs (Pydantic) for normalized records; ORM models (SQLModel/SQLAlchemy) for SQLite storage; raw-import JSON persisted for traceability.
  - ImportService: ingest → sanitize (Airlock) → normalize → persist (idempotent per week/platoon) with import logs.
  - SyncProvider abstraction: `LocalUploadProvider` (default) and `GoogleSheetsProvider` (optional, cached, keyed by file id/etag).
- Backend (`src/iron_view/api`):
  - FastAPI endpoints: upload/sync, import status, deterministic queries (gaps, trends, deltas), health; future `/insights` via AI provider.
  - Services module for business logic; CLI reuses the same services.
- Frontend (`frontend/`):
  - Local web app (React/Vite or Svelte) consuming the API only; self-hosted assets (no CDN); dashboards, filters (platoon/week/item), charts, and drill-down tables.
- AI layer (future):
  - `AIInsightProvider` interface with `SimulatedProvider` now; later `LLMProvider` using compact context from DB snapshots/deltas; results stored separately.

## Build Roadmap (incremental)
1) Baseline alignment (done): models/tests fixed, Airlock hardened.
2) Parsers: implement and test the three adapters against `דוחות פלוגת כפיר (1).xlsx`, `מסמך דוחות גדודי (1).xlsx`, `טופס דוחות סמפ כפיר. (תגובות) (1).xlsx`.
3) Persistence: define SQLite schema, migrations, ImportService with idempotency and raw capture.
4) Deterministic queries: gaps by platoon/week/item, weekly deltas, ammo/kesher status, variance vs. battalion summary.
5) API: FastAPI upload/sync, queries, status, health; rate limits/logging. (done)
6) Frontend: dashboard (filters, charts, tables), local assets, no CDN. (in progress: Vite React prototype connected to API)
7) Google Sheets sync (optional): provider with caching and configurable credentials; fallback to local upload.
8) AI layer (optional, later): plug-in provider; prompt hygiene and caching.

## Engineering Standards
- Python 3.10+; type hints mandatory; Pydantic models for external interfaces/DTOs; `default_factory` for mutable defaults.
- No global mutable state; dependency injection for services/adapters/settings.
- Error handling: raise explicit domain exceptions; log with context (file id, platoon, week); fail-soft on per-row errors with audit logs.
- Logging: structured where possible; avoid logging PII; include import ids.
- Testing: unit tests for adapters/queries; integration tests for ImportService (ingest → DB → query); API tests for endpoints; keep fixtures minimal and representative.
- Performance/robustness: tolerate column drift (header matching with tolerant maps); cache parsed files; idempotent imports keyed by week/platoon/source.

## Data Handling and Security
- Airlock strips PII columns; only sanitized fields reach models/DB.
- Credentials (e.g., Google service account) stored locally with restricted permissions; never commit secrets.
- Offline-first: local assets; external network only when sync provider is enabled.
- Auditability: store raw import JSON blobs and import logs; include file metadata (name, hash, source, timestamp).

## Design/UX Standards
- Clear RTL support where needed; typographic pairing (non-default fonts) and purposeful color system; avoid CDN fonts/icons in offline mode.
- Dashboard patterns: prominent KPIs, trends over time, gap tables with sorting/filtering, drill-down modals. Mantine components (Cards/Badges/Grids) for consistency; Chart.js lazily loaded; empty states and notifications for success/error.
- Accessibility: readable contrast, keyboard navigation for filters and tables; avoid text embedded in images.

## Maintenance Notes
- Update this document at each stage boundary (done → next), and when standards/architecture shift.
- Prefer local assets, deterministic builds, and reproducible tests (no live network unless explicitly configured for sync/AI).
- Scripts helper set: `reset-env.sh` (DB + frontend dist cleanup), `clean-ui.sh` (frontend dist cleanup), `test-build-run.sh` (pytest + UI build + run-local).

## Upcoming Release Plan — "קצה הרומח"
Superseded by the refreshed Execution Plan above. Use the new phases (0–6) as the single source of truth for implementation and approvals.

## Editing and Delivery Policy
- Code and docs: concise, English for code; Hebrew UI copy where appropriate. Keep ASCII unless existing file uses otherwise.
- Process: work phase-by-phase; share progress and await approval before moving to the next phase. One commit per approved phase.
- Quality: no shortcuts—prove correctness end-to-end (tests + manual smoke when relevant) before requesting approval.
- Style: follow existing patterns; add comments only where logic is non-obvious. Keep deterministic, offline-friendly defaults.
- Auth/Secrets: use `.env` for tokens/keys; do not hardcode secrets; preserve manual sync by default.
- Communication: reflect status/banners in UI; log meaningful errors; surface sync/etag/source info clearly.
