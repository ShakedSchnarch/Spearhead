# Forms Contract (Operational)

## Form A: Tank Commander Weekly Form
Purpose: per-tank weekly readiness.

Required metadata:
1. פלוגה
2. מספר טנק
3. תאריך דיווח
4. שם מדווח

Operational sections:
1. לוגיסטיקה
2. חימוש
3. תקשוב

Answer format for each item:
1. תקין
2. חסר
3. תקול
4. Optional short note when status is `חסר` or `תקול`.

## Form B: Company Assets Weekly Form
Purpose: weekly company-level equipment and support assets.

Required metadata:
1. פלוגה
2. תאריך דיווח
3. שם מדווח

Representative groups:
1. דוח צלם- נוספים
2. דוח ת"ת פלוגתי
3. ח"ח פלוגתי (חלפים)
4. שמנים פלוגתיים (`2510`, `2640`, `גריז 2040`, `גריז 4080`)
5. ציוד רנגלר/קשפל

Answer format:
1. תקין
2. חסר
3. תקול
4. Optional short note.

## Runtime API mapping
1. Tank form -> `POST /v1/ingestion/forms/events`
2. Company-assets form -> `POST /v1/ingestion/forms/company-assets`
