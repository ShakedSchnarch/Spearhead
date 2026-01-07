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

## Updated Execution Plan (Post-MVP → first customer release)
All steps keep existing functionality; only additive improvements. Each phase ends with an approval/commit.

### Phase 1: Google Sheets Sync (priority)
- Source of truth: per-platoon Google Form responses (כפיר/סופה/מחץ). Platoon is inferred from the sheet/file id; tanks identified by צ׳ טנק (no fixed counts).
- Week derivation: from timestamp/date column; store week_key for grouping.
- Schema drift: tolerant parsing (new columns kept as text), no breakage on added fields.
- ETag/304: skip unchanged downloads; log source (cache/remote), etag, last_sync, last_error in `/sync/status`.
- Tests: provider fakes for cache/etag/failure; API tests for `/sync/google` missing/invalid config + status payload.
- Deliverable: stable sync, week/platoon-aware ingestion, transparent status.

### Phase 2: Data shaping, calculations, and seeding
- Dynamic tank counts: derive per-platoon tank count from distinct צ׳ טנק per week; no hardcoded numbers.
- Calculations:
  - Zivud totals show only חוסר/בלאי (both platoon and battalion views).
  - Battalion zivud: per-platoon gaps + battalion total.
  - Ammo/Means: compute per-tank averages using dynamic tank counts.
  - P’arei Tzal’mim: include צ׳ טנק + שם המט״ק as provided.
- Exports: generate refreshed Excel outputs (platoon weekly summary and battalion summary) with the above logic (aligned/improved vs. existing examples).
- Seeding/reset: helper to clean DB and rerun sync-all for demo/QA.
- Tests: unit calc tests (averages/gaps), integration for two consecutive syncs (idempotent), smoke on export structure.

### Phase 3: View modes (Battalion vs. Platoon)
- Backend: optional platoon override for UI (non-breaking).
- Frontend: toggle Battalion/Platoon with persistent filters (platoon, section, topN); adjust KPIs/graphs per mode.
- QA: manual smoke for both modes.

### Phase 4: UX polish and messaging
- Clear upload/sync success/error messaging (Hebrew), KPI header (last import/sync time, cache/remote).
- Keep visuals; tighten labels/tables as needed for the new modes/data.

### Phase 5: Auth and ops
- Token flow verified (Authorized/Unauthorized); keep token empty for local dev.
- Maintain scripts; optionally add no-reload “prod” target.

### Phase 6: AI (optional)
- If enabled: smoke with real provider, redaction/limited context, source indicator (cache/remote) in UI.
- Otherwise remain simulated; document enablement.

### Phase 7: Docs and release
- Update README (run scripts, sync flow, modes, token usage) and keep/append release notes in this plan.
- Final QA: clean-db → sync/import → UI smoke; `scripts/test.sh`.

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
