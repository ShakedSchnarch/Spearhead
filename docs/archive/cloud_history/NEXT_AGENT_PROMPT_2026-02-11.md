# פרומפט לסוכן הקוד של מחר

אתה ממשיך את פרויקט Spearhead עבור גדוד 75.
יש לעבוד בעברית מול המשתמש, בצורה פרקטית, מסודרת וממוקדת דיפלוי.

## מה לקרוא קודם (לפי הסדר)
1. `docs/cloud/SESSION_HANDOFF_2026-02-10.md`
2. `docs/cloud/KFIR_FORM_SPEC_DRAFT.md`
3. `docs/cloud/FOCUSED_REDESIGN_ROADMAP.md`
4. `docs/ARCHITECTURE.md`
5. `docs/RUNBOOK.md`
6. `README.md`
7. Frontend:
   - `frontend-app/src/components/SimpleLogin.jsx`
   - `frontend-app/src/components/DashboardContent.jsx`
   - `frontend-app/src/config/unitMeta.js`
8. Backend ingestion/views:
   - `src/spearhead/v1/matrix_ingest.py`
   - `src/spearhead/v1/store_firestore.py`
   - `src/spearhead/v1/service.py`
   - `src/spearhead/api/routers/v1.py`

## מצב המערכת כרגע
- המערכת חיה ב‑Cloud Run, OAuth עובד, וה‑UI החדש כבר בפרודקשן.
- היקף גרסה נוכחית: כפיר בלבד; השוואה גדודית ריקה בכוונה כשיש פלוגה אחת.
- היעד הקרוב: קליטה יציבה של תשובות Google Form חדש והצגה אמינה של כשירות פלוגתית.

## פעולות חובה בתחילת הסשן
1. לאמת מצב בענן:
   - `gcloud config set project spearhead-stg`
   - בדיקת URL/revision/env של `spearhead-api`
2. לאמת מצב לוקאלי:
   - `./scripts/bootstrap-dev-env.sh`
   - `./scripts/test.sh -q`
   - `cd frontend-app && npm run lint && npm run build`
3. לסגור עם המשתמש אישור סופי על חוזה טופס כפיר:
   - שמות פריטים
   - תקן לכל פריט
   - פריטים קריטיים
   - פורמט תשובה: `תקין/חסר/תקול + פירוט קצר`

## יעד מסירה לסשן הבא
1. לקבע ולאשר חוזה טופס כפיר (`v1`).
2. לממש/לעדכן mapping קליטה מ‑Google Form אל אירועי `v1`.
3. להוכיח E2E על נתונים אמיתיים:
   - הזנת טופס
   - ingest/sync
   - הופעה נכונה בדשבורד הפלוגתי
4. לשמור על ארכיטקטורה פשוטה וזולה (שירות יחיד + Firestore).

## מגבלות חובה
- לא להוסיף יכולות AI/LLM בשלב הזה.
- לא לבנות היררכיית הרשאות מורכבת.
- להעדיף קונפיגורציה על hard-coding.
- לא לשבור OAuth/Cloud Run שעובדים כרגע.

## צורת עבודה מול המשתמש
- לשאול שאלות תוכן ממוקדות לפני נעילת סכמות.
- להסביר כל צעד GCP: מה עושים, למה, ומה ההשפעה על אבטחה/עלות.
- להעדיף פקודות `gcloud` שהמשתמש יכול להריץ ב‑VSCode.

## Definition of Done לסשן הבא
- המשתמש מאשר את מבנה טופס כפיר והתקנים.
- יש ingestion עובד מהטופס המאושר אל המערכת.
- הנתונים מוצגים בדשבורד בצורה אמינה.
- lint/build/tests עוברים והדוקומנטציה מעודכנת.
- ממתינים לאישור משתמש לפני commit/push.
