# IronView – Project Plan and Standards

## Vision and Scope
- Local-first operational dashboard for the S3/CO to ingest weekly company/battalion readiness spreadsheets and serve web reports.
- Support two intake modes: local file upload (default/offline) and optional Google Sheets pull (with cached copies and explicit credentials).
- Deterministic analytics first (inventory/status deltas, gaps, trends), with an opt-in AI layer later for anomaly detection and long-range insights.

## Current Stage
- Stage 1 complete: aligned domain models (safe defaults, optional reporter/notes), fixed Airlock robustness, and all tests are green.
- Stage 2 complete: adapters for platoon loadout, battalion summary, and form responses implemented with tests on the latest files.
- Next: Stage 3 DB schema + ImportService (idempotent ingest with raw capture), then deterministic queries.

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
5) API: FastAPI upload/sync, queries, status, health; rate limits/logging.
6) Frontend: dashboard (filters, charts, tables), local assets, no CDN.
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
