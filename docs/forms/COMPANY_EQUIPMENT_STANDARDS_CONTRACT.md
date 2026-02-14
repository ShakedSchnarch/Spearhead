# Company Equipment & Standards Contract (Commander Review)

Updated: 2026-02-15

## Scope

- Active companies: כפיר, מחץ, סופה
- Standards version: 2026.1
- Tank blueprint source: `docs/forms/kfir_company_form_blueprint.json`
- Tank contract CSV (full list): `docs/forms/contract_tank_items.csv`
- Company-assets contract CSV (full list): `docs/forms/contract_company_assets.csv`

## Contract Notes For Approval

- Baseline contract currently applies to Kfir/Mahatz/Sufa equally unless company-level deltas are approved.
- Sections are fixed: `Logistics`, `Armament`, `Communications`.
- Item status in forms: `תקין`, `חסר`, `תקול` (note required for `חסר`/`תקול`).
- Critical items list (operational):
  - חבל פריסה
  - פטיש 5
  - ראשוני
  - איציק
  - לום
  - מאריך חש"ן
  - בייבי קוני
  - משלק
  - פטיש קילו
  - מפתח Y
  - 2מפתח פלטות
  - בוקסה 1\5\16
  - ידית כוח חצי
  - ידית כוח 3\4
  - מחט ירי
  - אלונקה
  - מקלות חוטר

## Tank Equipment Breakdown By Section

| Section | Family | Items |
|---|---|---:|
| Armament | kashpal | 3 |
| Communications | communications_core | 6 |
| Communications | device_issue_matrix | 14 |
| Communications | office | 13 |
| Communications | ranger | 10 |
| Logistics | ammo | 15 |
| Logistics | zivud | 68 |

## Company Assets Breakdown

| Section | Group | Items |
|---|---|---:|
| Armament | חלפים | 3 |
| Armament | שמנים | 4 |
| Company Assets | דיווחים פלוגתיים | 4 |

## Company-Level Review Matrix

| Company | Uses Baseline Tank Contract | Uses Baseline Company-Assets Contract | Approval Status | Notes |
|---|---|---|---|---|
| כפיר (Kfir) | Yes | Yes | Pending Commander Review | |
| מחץ (Mahatz) | Yes | Yes | Pending Commander Review | |
| סופה (Sufa) | Yes | Yes | Pending Commander Review | |

## Next Step

After commander approval, update any deltas directly in `config/operational_standards.yaml` and regenerate this contract before final Google Forms publication.
