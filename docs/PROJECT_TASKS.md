# Spearhead Master Tasks

Last updated: 2026-02-14

## How to use
1. Keep this file as the single source of truth for active work.
2. Update status at the start and end of every implementation step.
3. Keep priorities strict (`P0` highest, then `P1`, `P2`).

## Active backlog

| ID | Priority | Status | Scope | Task | Exit criteria |
|---|---|---|---|---|---|
| T-001 | P0 | In Review | UI | Company dashboard polish (chart placement, click-through, RTL numeric rendering, clearer hierarchy) | Manual review passes requested UX checklist |
| T-002 | P0 | In Review | UI | Battalion dashboard comparison polish (cards + trends + critical gaps visualization) | Commander can compare companies in one screen without ambiguity |
| T-003 | P0 | In Progress | Forms | Finalize two production Google Forms (tank commander + company assets) | Forms are created in Google, linked Sheets IDs captured, ingestion verified |
| T-004 | P0 | Completed | Data | Connect Mahatz + Sufa weekly sources to ingestion flow | Both companies appear in weekly battalion views with real data |
| T-005 | P1 | Completed | AI | Add battalion AI analysis block with offline-safe fallback and optional remote provider | Dashboard shows deterministic fallback and optional remote AI output |
| T-006 | P1 | In Review | Ops | Cloud hardening pass (secrets, IAM least privilege, cost controls, scheduler strategy) | Runbook checklist completed and validated in cloud |
| T-007 | P1 | Pending | Architecture | Repository cleanup (duplicate docs/scripts/config drift) and structure consistency pass | Architecture/test/readme checks are aligned and no conflicting docs remain |
| T-008 | P1 | Completed | Quality | Expand tests for trends, AI endpoint, and company-assets contracts | Test suite covers added behavior and passes in CI/local |

## Completed recently

| ID | Date | Notes |
|---|---|---|
| C-001 | 2026-02-14 | Added standards-driven model for item standards and company-assets grouping via `config/operational_standards.yaml` |
| C-002 | 2026-02-14 | Added tank drawer full inventory table and report-status badge per tank card |
| C-003 | 2026-02-14 | Added battalion/company trend foundations (including weekly readiness) |
| C-004 | 2026-02-14 | Compact dashboard layout pass: denser chart grid, side-by-side operational blocks, collapsible detailed tables |
| C-005 | 2026-02-14 | Release gate hardening: `scripts/release-check.sh` now validates lint, merge markers, and TODO/FIXME markers |
| C-006 | 2026-02-14 | Added remote-AI API test coverage for `/v1/views/battalion/ai-analysis` with mocked client |
| C-007 | 2026-02-14 | Final pre-release local smoke completed (UI + battalion endpoints + remote AI + multi-company ingestion duplicates check) |
| C-008 | 2026-02-14 | Improved battalion AI prompt/context + structured UI rendering, fixed company color system, compacted ammo table UX, and generated commander-review standards contract docs |
| C-009 | 2026-02-14 | Added cloud access-control SOP + safe authorized-users update script (`manage-authorized-user.sh`) and fixed OAuth permission onboarding flow |
