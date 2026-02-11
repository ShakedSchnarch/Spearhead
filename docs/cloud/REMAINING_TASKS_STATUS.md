# Remaining Tasks Status (as of 2026-02-10)

## Completed Now (No External Dependency)
1. UI redesign shipped to production Cloud Run.
2. Professional battalion/company branding with logos integrated.
3. Session handoff and continuation docs created.
4. Dev environment bootstrap script added:
   - `scripts/bootstrap-dev-env.sh`
5. Test runner stabilized to avoid broken virtualenv activation path:
   - `scripts/test.sh`
6. README and runbook updated with consistent local workflow.

## Blocked by User Validation / External Systems
1. Final approval of Kfir form contract (`docs/cloud/KFIR_FORM_SPEC_DRAFT.md`).
2. Actual creation/update of the Google Form fields after approval.
3. Real response ingestion validation from the approved Google Form sheet.
4. Battalion comparison rollout (requires at least 2 companies with data).

## Immediate Next Action for Next Session
1. Review and approve Kfir form spec line-by-line with user.
2. Create/adjust Google Form accordingly.
3. Execute end-to-end ingest and verify dashboard output.

## Backlog (After Core Scope Is Stable)
1. Define access approvals and company-scoped authorization flow.
2. Repository cleanup and structured documentation pass.
3. Add CI/CD routine with automated tests (frontend + backend).
4. Document a clear onboarding mechanism for adding new companies, forms, and tracked items with minimal code changes.
