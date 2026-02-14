# פרומפט לסוכן הקוד הבא — 2026-02-12

עבוד מול המשתמש בעברית, באופן פרקטי וממוקד MVP מבצעי.
המטרה: לסיים E2E אמיתי לטופס כפיר (Form -> Sync -> Dashboard).

## מה לקרוא קודם
1. `docs/cloud/SESSION_HANDOFF_2026-02-11.md`
2. `docs/cloud/TOMORROW_TASKS_2026-02-12.md`
3. `docs/cloud/KFIR_FORM_SPEC_DRAFT.md`
4. `docs/forms/README.md`
5. `docs/forms/kfir_company_form_blueprint.json`
6. `docs/forms/kfir_google_form_apps_script.gs`

## מצב ענן נכון לפתיחת יום
- Project: `spearhead-stg`
- Region: `europe-west1`
- Service: `spearhead-api`
- Active revision: `spearhead-api-00018-tfs`
- Service URL: `https://spearhead-api-wrkqihn7zq-ew.a.run.app`
- Required secrets exist:
  - `SPEARHEAD_API_TOKEN`
  - `SPEARHEAD_OAUTH_CLIENT_ID`
  - `SPEARHEAD_OAUTH_CLIENT_SECRET`
  - `SPEARHEAD_AUTHORIZED_USERS`

## פעולות חובה בתחילת הסשן
1. אמת ענן:
   - `gcloud config set project spearhead-stg`
   - בדוק `status.url` + env + secrets bind.
2. אמת local:
   - `./scripts/test.sh -q`
   - `cd frontend-app && npm run lint && npm run build`
3. סגור עם המשתמש אישור סופי ל-spec כפיר לפני שינויי mapping.

## הגדרת הצלחה לסשן
1. Google Form אמיתי נוצר ומחובר ל-Sheet.
2. Sheet ID מחובר למערכת env/secrets.
3. הנתונים נטענים ומוצגים בדשבורד בפועל.
4. כל ולידציה עוברת (lint/build/tests).

## עקרונות עבודה
- לא להוסיף AI/LLM.
- לא להוסיף הרשאות מורכבות מעבר לדרוש.
- להעדיף קונפיג על hard-code.
- לבצע קומיטים קטנים אחרי כל שלב מאושר.
- לפני כל deploy: בדיקות מקומיות מלאות.
