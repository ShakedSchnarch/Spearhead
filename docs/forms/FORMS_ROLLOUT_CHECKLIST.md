# Forms Rollout Checklist

Last updated: 2026-02-14

## Current status
1. Generator is ready (`scripts/forms/generate-google-form-apps-script.py`).
2. Script output is ready (`docs/forms/kfir_google_form_apps_script.gs`).
3. Two forms are defined in the script:
   - Tank commander weekly form
   - Company assets weekly form
4. Pending: create/publish forms in Google and bind response sheet IDs to runtime config.

## Rollout steps
1. Regenerate script after any standards change:
```bash
python3 scripts/forms/generate-google-form-apps-script.py --standards config/operational_standards.yaml
```
2. Open [Google Apps Script](https://script.google.com/) and paste `docs/forms/kfir_google_form_apps_script.gs`.
3. Run:
   - `createSpearheadTankCommanderForm()`
   - `createSpearheadCompanyAssetsForm()`
4. Save:
   - Published form URL
   - Linked response Google Sheet ID
   - Form edit URL (for controlled updates)
5. Update runtime config:
   - `GOOGLE__FILE_IDS__FORM_RESPONSES` for tank form response sheet IDs per company
   - (If separated) keep company-assets response sheet ID in deployment notes/runbook
6. Submit one test response in each form and verify ingestion:
   - `POST /v1/ingestion/forms/events`
   - `POST /v1/ingestion/forms/company-assets`

## Acceptance checklist
1. All required fields are clear in Hebrew and no duplicate questions exist.
2. Item labels include standards where available.
3. Response exports map to the expected parser contract.
4. Dashboard shows new responses in:
   - tank cards
   - inventory drawer
   - company assets tab
   - battalion comparison

