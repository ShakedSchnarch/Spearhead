# IronView – Project Plan and Standards

## Vision and Scope
- Local-first operational dashboard for the S3/CO to ingest weekly company/battalion readiness spreadsheets and serve web reports.
- Support two intake modes: local file upload (default/offline) and optional Google Sheets pull (with cached copies and explicit credentials).
- Deterministic analytics first (inventory/status deltas, gaps, trends), with an opt-in AI layer later for anomaly detection and long-range insights.

## Current Stage (Completed)
- Stage 1: Domain alignment (Pydantic models with safe defaults), Airlock hardened, tests green.
- Stage 2: Adapters for platoon loadout, battalion summary, and form responses; tests against latest files (1).
- Stage 3: SQLite schema + ImportService (hash-based idempotency, raw capture, JSON-safe fields); tests.
- Stage 4: Deterministic query layer (totals, gaps, by-platoon, form status, delta, variance vs summary); tests.
- Stage 5: FastAPI layer exposing imports/queries/health, CORS, static serve of frontend dist at `/app`; integration tests.
- Stage 6 (prototype): React (Vite) dashboard with uploads, Chart.js (totals/gaps), delta/variance panels, form status JSON, API base selector. CORS-enabled API; frontend build served by API when `frontend-app/dist` exists.
- Google Sheets sync implemented (mandatory path forward): `sync/google` endpoint using service account/API key + configured file_ids; unit-tested with a fake provider.
- Stage 7: Frontend polish — filters (platoon/section/topN), sortable tables for delta/variance, trendlines, AI surface, local assets.
- Stage 8: API hardening — optional auth (token/basic), request-size guard, request logging, unified error responses.
- Stage 9: Google Sheets sync robustness — retry/backoff, cache fallback, sync status endpoint.
- Stage 10: AI layer — simulated/HTTP client abstraction with safe prompt/context, caching, deterministic fallback, `/insights` endpoint and UI surface.

## Next Stages (To Do)
11) Ops/docs: update README and PROJECT_PLAN with run commands (uvicorn + npm build/dev), sample .env (google settings, api key), Docker/Docker-compose, release checklist.

## Execution Plan – Milestones and Subtasks

### Stage 7: Frontend polish (UX and data rendering)
- Filters: platoon/section/week/topN selectors wired to API params; debounce + defaults; persist selection in localStorage.
- Tables: sortable, paginated tables for totals/gaps/delta/variance; color-coded delta/variance (up/down) and readable units.
- Charts: trendlines for key items over time; add variance/delta cards with sparklines; keep assets local (no CDN fonts/icons).
- UX: responsive layout for desktop/mobile; loading/error states; API base selector retained; accessibility (keyboard focus, contrast).
- Validation: manual QA against sample data; add frontend unit/snapshot tests where feasible.

### Stage 8: API hardening (auth, limits, logging)
- Auth: optional API token/basic auth via settings; middleware/dependency to enforce on mutable endpoints (imports/sync) and optionally queries.
- Limits: upload size cap; sensible timeouts/body size in FastAPI/uvicorn; reject oversize with clear error.
- Observability: structured request/response logging with request IDs; minimal PII; health endpoint stays open.
- Errors: unified error responses with codes; graceful handling for bad files/queries; CORS stays permissive for LAN.
- Validation: new tests for auth/limits/error cases; update config docs for enabling/disabling.

### Stage 9: Google Sheets sync robustness
- Config: document service_account_file/API key, file_ids, enable flag; sample .env values; safe defaults when disabled.
- Resilience: retry with backoff on transient errors; caching of last-good downloads; ETag/hash checks to skip unchanged files.
- Status: endpoint exposes last sync status/timestamps per sheet; include counts inserted/skipped; clear errors for missing config.
- Validation: unit tests with fake provider covering retry/backoff/cache/status; doc updates on how to run sync.

### Stage 10: AI layer (LLM client + integration)
- Client: new LLM client abstraction with safe prompt template, context trimming, caching, and deterministic fallback (rule-based) when disabled or errors.
- Data: store AI outputs linked to imports/queries; schema updates as needed with migrations/backfill path.
- API/UI: expose AI insights endpoint; surface in UI cards/tables with confidence and provenance; allow opt-out via config.
- Safety: guardrails for prompt inputs, token budgets, redaction of sensitive fields; offline-friendly default (simulated provider).
- Validation: unit tests for client caching/fallback; integration test for API surface; config docs for enabling with env vars/keys.

### Stage 11: Ops/docs and delivery
- Developer flow: consolidate run commands (uvicorn, npm dev/build), one-liner for serving built UI, and watch-mode guidance.
- Configuration: sample `.env.example` for API token, Google creds/ids, AI provider keys, size limits; reference in README.
- Packaging: optional Dockerfile + docker-compose (API + frontend build) with volumes for data; document build/run steps.
- QA: final test pass (unit + API + sync); lint/format if configured; cut changelog/release notes.

## Architecture (Current)
- Data: Adapters (xlsx), DTOs, SQLite storage, ImportService (hash idempotency), Google Sync provider/service, QueryService (deterministic).
- API: FastAPI app factory; imports, queries, sync/google, health; static serve of `frontend-app/dist` at `/app` if present.
- Frontend: `frontend-app/` (Vite React) consuming API; builds to dist.
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
- Dashboard patterns: prominent KPIs, trends over time, gap tables with sorting/filtering, drill-down modals.
- Accessibility: readable contrast, keyboard navigation for filters and tables; avoid text embedded in images.

## Maintenance Notes
- Update this document at each stage boundary (done → next), and when standards/architecture shift.
- Prefer local assets, deterministic builds, and reproducible tests (no live network unless explicitly configured for sync/AI).
