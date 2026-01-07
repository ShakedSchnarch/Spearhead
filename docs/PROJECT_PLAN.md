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

## Updated Execution Plan (Post-MVP → first customer release)
All steps keep existing functionality; only additive improvements. Each phase ends with an approval/commit.

### Phase 1: Google Sheets Sync (done)
- Source of truth: per-platoon Google Form responses (כפיר/סופה/מחץ). Platoon inferred from the sheet/file id; tanks identified by צ׳ טנק (no fixed counts).
- Week derivation: from timestamp/date column; store week_key for grouping.
- Schema drift tolerance: added columns kept as text.
- ETag/304 cache, retry/backoff, `/sync/status` shows etag/source/cache/last_sync/error.
- Tests: provider fakes for cache/etag/failure; API tests for `/sync/google`.

### Phase 2: Resilient data shaping (config-driven, non-hardcoded) — Done
- Config file (`config/fields.yaml`): header aliases per family (zivud/ammo/means/issues/parsim), tank_id/timestamp/commander, platoon inference (file id/name), gap/ok tokens.
- Normalization: slug headers (strip punctuation/spacing/diacritics); resolve via config with wildcards (“דוח זיווד [*]”, “סטטוס ציוד קשר [*]”); avoid hardcoded strings.
- Schema drift visibility: keep unknown columns in raw payload; log “unmapped headers”; store per-import schema snapshot (expose via `/sync/status` or sidecar JSON).
- Validation: if essential columns (tank_id/timestamp) missing → 422 with clear message; otherwise warn on unmapped.
- Calculations (same behavior): zivud gaps only, ammo/means per-tank averages, dynamic tank counts per platoon/week, פערי צלמים if present, commander capture.
- Exports: platoon/battalion XLSX fed by normalized names; commander/tank ids in פערי צלמים; skip/notify when categories empty.
- Tests: fuzzed headers (aliases/spacing), added columns, idempotent dual sync, export smoke.
- Deliverable: parsing/analytics driven by config, resilient to sheet changes.

### Phase 3: View modes (Battalion vs. Platoon) — Done
- Backend: optional platoon override for UI; normalized zivud/ammo/means summaries via `/queries/forms/summary`.
- Frontend: toggle Battalion/Platoon with persistent filters (platoon/section/topN/week); KPIs + sync source/etag surfaced; banners for success/error.
- QA: manual smoke + pytest (includes summary modes).

### Phase 4: UX polish and messaging — Done
- Hebrew success/error messaging for import/sync/queries and KPI with time/source/etag.
- Full RTL support for the user UI, navigation anchors, friendly empty states.

### Phase 5: Auth and ops — Done
- Token/basic auth wired end-to-end; UI token field stores locally.
- Auth smoke documented in README; keep token empty for local dev by default.
- Consolidated runner is optional; existing scripts cover API/UI/test flows.

### Phase 6: AI (optional)
- If enabled: smoke with real provider, redaction/limited context, source indicator (cache/remote) in UI.
- Otherwise remain simulated; document enablement.

### Phase 7: Docs and release — Done
- README updated (scripts, sync flow, modes, token usage, auth smoke); release notes appended here.
- QA run (local samples): clean-db, import + exports generated, reports under `reports/` (platoon_כפיר_2026-W01.xlsx, battalion_2026-W01.xlsx), pytest green.
- Next: tag internal release and ensure schema snapshots/config/fields.yaml are committed.

## Release Notes (Internal)
- Phase 2: Config-driven parsing (fields.yaml), header normalization with wildcards, schema snapshots, validation, and unmapped logging.
- Phase 3: Battalion/Platoon view modes; `/queries/forms/summary`; frontend toggle + KPIs and sync source/etag.
- Phase 4: UX polish (Hebrew UI, RTL, navigation anchors, empty states, auth banners).
- Phase 5: Auth wired end-to-end (token/basic, UI token field); auth smoke documented.
- Phase 7: QA pass with local fixtures; reports emitted to `reports/`; pytest green.

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
