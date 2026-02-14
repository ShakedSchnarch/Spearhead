# Data Sources Registry

## Source of truth
Use `data/external/company_sources/registry.json` as the canonical registry for company matrix sources.

## Current companies
1. Kfir
   - Sheet ID configured in registry.
   - Runtime status: active.
2. Mahatz
   - Local cache: `data/external/company_sources/mahatz_matrix.xlsx`.
   - Runtime status: ready.
3. Sufa
   - Local cache: `data/external/company_sources/sufa_matrix.xlsx`.
   - Runtime status: ready.

## Operational notes
1. Weekly data is represented by sheet tabs named `שבוע N`.
2. Sufa has non-parseable tabs for some weeks (e.g. structure drift in week 4/5); parser currently warns and skips those sheets.
3. Matrix files include embedded company-assets blocks (e.g. `דוח צלם- נוספים`, `ח"ח פלוגתי`, oils). These should be reported via the dedicated company-assets form flow.

## Ingestion commands
1. Single company matrix ingestion:
```bash
PYTHONPATH=src ./scripts/cloud/ingest-matrix-sheet.py --sheet-id <ID> --company <Company> --api-base-url <URL> --api-token <TOKEN>
```
2. Multi-company ingestion from registry:
```bash
PYTHONPATH=src ./scripts/cloud/ingest-company-sources.py --api-base-url <URL> --api-token <TOKEN>
```
