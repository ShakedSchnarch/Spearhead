# Kfir Platoon File Analysis (Week 7 Baseline)

Source workbook analyzed:
- Google Sheet ID: `13P9dOUSIc5IiBrdPWSuTZ2LKnWO56aDU1lJ7okGENqw`
- Exported and parsed from: `שבוע 7`

Machine-readable extraction:
- `data/kfir_week7_form_schema.json`

## Main findings

1. The sheet is not one flat table; it contains multiple operational sub-tables.
2. It includes both per-tank status data and special sections (communications, office/ranger assets, issue matrices).
3. Existing Google Form export in this repo (`docs/archive/samples/טופס דוחות סמפ כפיר. (תגובות).xlsx`) already covers most of the same logical domains.

## Detected section counts in Week 7

- Zivud / inventory items: `68` items (including edge rows like `כיסוי תובה`, `משאבת סולר`)
- Ammo / armament items: `15` items
- Core communications checklist: `6` items
- Ranger assets: `10` items
- Office assets: `13` items
- Kashpal assets: `3` items
- Device issue matrix: `14` tracked device types

## Practical implications for the new Google Forms

1. A single very long form is possible, but will be heavy for weekly reporting.
2. Recommended baseline is to keep one main weekly tank form, with clear sections:
- Armament
- Logistics
- Communications
- Device/issue details
3. If needed, company-level assets (office/ranger/kashpal) can be split into a separate role form later.

## Next action

Use `data/kfir_week7_form_schema.json` as the source-of-truth seed to generate the new Google Forms question set, while preserving existing backend field mapping conventions.
