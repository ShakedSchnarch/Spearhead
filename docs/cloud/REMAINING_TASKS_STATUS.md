# Remaining Tasks Status (as of 2026-02-14)

## Completed
1. Cloud foundation is active on GCP (Cloud Run + Firestore + OAuth + Secret Manager baseline).
2. Authentication flow is stable (Google OAuth + session handoff to frontend).
3. Dashboard UI was redesigned for battalion/company modes with Hebrew operational focus.
4. Company visual cards now use clearer progress bars (instead of donut-only cards).
5. Tank cards include report-state handling (`דיווח השבוע` / `לא דיווח`) and drill-down drawer.
6. Local workflow was aligned:
   - `scripts/setup-venv.sh`
   - `scripts/run-local.sh`
   - `scripts/local-dev.sh` (`start|stop|status|logs`)
7. Environment docs were aligned:
   - `.env.example`
   - `docs/cloud/ENV_SETUP_CHECKLIST.md`
8. Forms track was bootstrapped:
   - `docs/forms/kfir_company_form_blueprint.json`
   - `docs/forms/kfir_tank_ids.json`
   - `docs/forms/kfir_google_form_apps_script.gs`
9. Battalion comparison consistency was completed end-to-end:
   - API now keeps canonical company names (`Kfir/Mahatz/Sufa`, with `Palsam` aliases preserved for future enablement).
   - `/v1/views/battalion` now includes configured companies even when no data exists.
   - Alias normalization expanded for `פלס״מ`/`palsam` across parser/router/repository.
   - Regression tests added and passing.
10. Company-level reporting foundation was added:
   - New ingestion endpoint: `POST /v1/ingestion/forms/company-assets`.
   - New query views:
     - `GET /v1/views/companies/{company}/assets`
     - `GET /v1/views/companies/{company}/tanks/{tank_id}/inventory`
   - Company tank response now includes:
     - `critical_gaps_table`
     - `ammo_averages`
     - `trends`
11. Docs were flattened:
   - Dated cloud handoff/prompt docs moved to `docs/archive/cloud_history/`.
   - Active docs consolidated under:
     - `docs/cloud/WORKING_PLAN.md`
     - `docs/cloud/DATA_SOURCES.md`
     - `docs/forms/FORMS_CONTRACT.md`
12. Multi-company ingestion helper and source registry were added:
   - `data/external/company_sources/registry.json`
   - `scripts/cloud/ingest-company-sources.py`
13. Access-control operations were hardened:
   - Added onboarding runbook: `docs/cloud/ACCESS_CONTROL_RUNBOOK.md`
   - Added safe user-role updater: `scripts/cloud/manage-authorized-user.sh`
   - Clarified two-layer access model (Google OAuth test users + app authorized-users secret).

## In Progress
1. Real Kfir E2E closure (Google Form -> Sync -> Dashboard) in cloud runtime.
2. Company dashboard UX polish pass (inventory table ergonomics + duplication cleanup).
3. Battalion AI analysis block with offline-safe deterministic fallback and optional remote provider.

## Blocked by Product/Domain Approval
1. Final standards for the small set of unresolved items marked `לא מוגדר`.
2. Final rollout decision for company-assets fields that are optional by company (if any).

## Immediate Next Steps
1. Create real Google Forms (tank commander + company assets) from generated Apps Script.
2. Connect response Sheet IDs in env/secrets and verify ingestion for both endpoints.
3. Verify company dashboard with real data:
   - tank color cards + report badge
   - tank inventory table in drawer
   - critical gaps + ammo averages + trends
   - company assets tab
4. Run battalion expansion ingestion (Kfir/Mahatz/Sufa) via registry script.

## Deferred Backlog (after MVP stability)
1. Company-scoped authorization workflow and access approval management.
2. CI/CD pipeline with automated backend/frontend test gates.
3. Test coverage expansion for analytics/read-model regressions.
4. Clear onboarding guide for adding a new company/form with minimal code changes.
