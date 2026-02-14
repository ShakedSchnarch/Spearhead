# Google Forms Track

This folder contains the active artifacts and generators for the production forms flow.

## Current outputs

- `docs/forms/kfir_company_form_blueprint.json`
  - Generated from `data/kfir_week7_form_schema.json`
  - Uses fixed answer format: `תקין / חסר / תקול` + short note on missing/faulty items.
- `config/operational_standards.yaml`
  - Active operational standards catalog (enabled companies, critical items, company-assets groups, per-item standards).
  - Changing standards in this file updates both dashboard behavior and generated forms.
- `docs/forms/kfir_tank_ids.json`
  - Canonical Kfir tank IDs for the form dropdown.
- `docs/forms/kfir_google_form_apps_script.gs`
  - Generated Google Apps Script that creates:
    - weekly tank-commander form
    - dedicated company-assets form

## Regeneration

```bash
python3 scripts/forms/generate-kfir-form-blueprint.py
python3 scripts/forms/generate-google-form-apps-script.py \
  --standards config/operational_standards.yaml
```

## Deploy the form script (manual)

1. Open [script.google.com](https://script.google.com/).
2. Create a new standalone Apps Script project.
3. Replace `Code.gs` with the content of `docs/forms/kfir_google_form_apps_script.gs`.
4. Run:
   - `createSpearheadTankCommanderForm()`
   - `createSpearheadCompanyAssetsForm()`
5. Copy generated Form URLs + linked response Sheet IDs.
6. Update runtime config for response sheets:
   - `GOOGLE__FILE_IDS__FORM_RESPONSES` with the new responses sheet ID.

## Contract reference

See `docs/forms/FORMS_CONTRACT.md`.

## Rollout checklist

Use `docs/forms/FORMS_ROLLOUT_CHECKLIST.md` for the production handoff (creation, sheet IDs, ingestion verification).

## Legacy reference

If you need historical context from the old form shape:
- `docs/forms/LEGACY_FORM_ANALYSIS.md`
