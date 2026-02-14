# Working Plan (Active)

## Mission
Deliver an operationally focused Spearhead runtime for battalion 75 with:
1. Tank-level weekly readiness reporting.
2. Dedicated company-assets reporting.
3. Reliable battalion/company dashboard views.

## Locked Principles
1. MVP-first, operational clarity over feature sprawl.
2. AI is optional and must be offline-safe by default (deterministic fallback when remote provider is unavailable).
3. Config-driven behavior over hard-coded unit-specific logic.
4. Small verifiable steps with tests/lint/build before deploy.

## Current Delivery Stages
1. Stage 1: Data+Docs alignment
   - Clean active documentation set.
   - Keep historical dated notes under `docs/archive/cloud_history/`.
   - Add multi-company source registry and ingestion helper.
2. Stage 2: Data contracts
   - Keep tank flow on `/v1/ingestion/forms/events`.
   - Add company-assets flow on `/v1/ingestion/forms/company-assets`.
   - Expose company assets and full tank inventory query views.
3. Stage 3: Company dashboard completion
   - Tank cards: color + report badge.
   - Tank drawer: full inventory table.
   - Company cards/tables: critical gaps, ammo averages, weekly trends.
   - Dedicated company-assets tab.
4. Stage 4: Forms rollout
   - Professional Hebrew Google Form for tank commanders.
   - Separate Hebrew Google Form for company assets.
   - Rollout order: Kfir -> Mahatz -> Sufa.

## Out of Scope (for now)
1. Palsam rollout.
2. Complex authorization workflows.

## References
1. `docs/cloud/REMAINING_TASKS_STATUS.md`
2. `docs/cloud/DATA_SOURCES.md`
3. `docs/forms/FORMS_CONTRACT.md`
