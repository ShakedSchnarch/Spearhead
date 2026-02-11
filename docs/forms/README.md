# Google Forms Track (Draft)

This folder contains the active artifacts for the new modular forms flow.

## Current outputs

- `docs/forms/kfir_company_form_blueprint.json`
  - Generated from `data/kfir_week7_form_schema.json`
  - Uses fixed answer format: `תקין / חסר / תקול` + short note on missing/faulty items.
- `docs/forms/kfir_tank_ids.json`
  - Canonical Kfir tank IDs for the form dropdown.
- `docs/forms/kfir_google_form_apps_script.gs`
  - Generated Google Apps Script draft that creates:
    - weekly Kfir tank form
    - draft company-assets form

## Regeneration

```bash
python3 scripts/forms/generate-kfir-form-blueprint.py
python3 scripts/forms/generate-google-form-apps-script.py
```

## Deploy the form script (manual, 3 minutes)

1. Open [script.google.com](https://script.google.com/).
2. Create a new standalone Apps Script project.
3. Replace `Code.gs` with the content of `docs/forms/kfir_google_form_apps_script.gs`.
4. Run `createSpearheadKfirWeeklyForm()` once (authorize permissions).
5. Copy generated Form URL + linked response Sheet ID.
6. Update runtime config:
   - `GOOGLE__FILE_IDS__FORM_RESPONSES` with the new responses sheet ID.

## What is still pending (domain approval)

1. Final approved item list (especially Armament families).
2. Final standards for items where standard is missing.
3. Final wording/order for Google Forms sections.
4. Battalion-wide rollout order (Kfir first, then Mahatz/Sufa/Palsam).
