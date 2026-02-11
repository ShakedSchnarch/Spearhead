# Remaining Tasks Status (as of 2026-02-11)

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

## In Progress
1. Battalion comparison polish:
   - show all companies consistently
   - keep no-data companies marked as `אין דיווחים`
2. Final repository cleanup pass (remove leftovers, align docs/scripts naming).

## Blocked by Product/Domain Approval
1. Final approved item list for Kfir form (especially Armament families and standards).
2. Final wording/order for Google Form sections.
3. Approved company-assets form content (assistant CO weekly form).

## Immediate Next Steps
1. Approve/fix Kfir item list and standards.
2. Create the real Google Form from generated Apps Script.
3. Connect new response sheet ID in env/secrets and verify end-to-end sync.
4. Expand from Kfir-only to battalion-wide sources (Mahatz, Sufa, Palsam).

## Deferred Backlog (after MVP stability)
1. Company-scoped authorization workflow and access approval management.
2. CI/CD pipeline with automated backend/frontend test gates.
3. Test coverage expansion for analytics/read-model regressions.
4. Clear onboarding guide for adding a new company/form with minimal code changes.
