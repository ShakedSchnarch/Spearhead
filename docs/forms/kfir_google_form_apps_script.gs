function createSpearheadForms() {
  createSpearheadTankCommanderForm();
  createSpearheadCompanyAssetsForm();
}

function createSpearheadTankCommanderForm() {
  const form = FormApp.create("קצה הרומח | דוח מפקד טנק שבועי");
  form.setDescription("טופס שבועי למפקד טנק. מילוי ברור, קצר ועקבי: תקין / חסר / תקול + פירוט תקלות לפי צורך.");
  form.setCollectEmail(true);
  form.setAllowResponseEdits(true);

  form.addListItem()
    .setTitle("פלוגה")
    .setChoiceValues(["כפיר", "מחץ", "סופה"])
    .setRequired(true);
  form.addListItem()
    .setTitle("מספר טנק")
    .setChoiceValues(["צ׳329", "צ׳337", "צ׳423", "צ׳427", "צ׳456", "צ׳631", "צ׳636", "צ׳637", "צ׳653", "צ׳670", "צ׳676"])
    .setRequired(true);
  form.addDateItem().setTitle("תאריך דיווח").setRequired(true);
  form.addTextItem().setTitle("שם מדווח").setRequired(true);
  form.addParagraphTextItem().setTitle("הערת פתיחה (אופציונלי)");

  // --- לוגיסטיקה ---
  form.addPageBreakItem().setTitle("לוגיסטיקה");
  form.addGridItem()
    .setTitle("סטטוס פריטים - לוגיסטיקה")
    .setRows(["חבל פריסה (תקן: 1)", "פטיש 5 (תקן: 1)", "ראשוני (תקן: 1)", "איציק (תקן: 1)", "לום (תקן: 1)", "מאריך חש\"ן (תקן: 1)", "בייבי קוני (תקן: 1)", "משלק (תקן: 1)", "פטיש קילו (תקן: 1)", "מפתח Y (תקן: 1)", "2מפתח פלטות (תקן: 2)", "בוקסה 1\\5\\16 (תקן: 1)", "ידית כוח חצי (תקן: 1)", "ידית כוח 3\\4 (תקן: 1)", "מחט ירי (תקן: 2)", "אלונקה (תקן: 1)", "מקלות חוטר (תקן: 9)", "מפתח כליר (תקן: 1)", "תיק כלי עבודה (תקן: 1)", "בוקסה 1 1\\2 (תקן: 1)", "בוקסה 9\\16 (תקן: 1)", "מאריך ארוך 1\\2 (תקן: 1)", "מאריך קצר 1\\2 (תקן: 1)", "מאריך ארוך 3\\4 (תקן: 1)", "מאריך קצר 3\\4 (תקן: 1)", "מפרק חצי (תקן: 1)", "גריקן 20 ליטר (תקן: 1)", "פוט שוש (תקן: 1)", "גבקה (תקן: 1)", "פטיש עיסית (תקן: 1)", "אלונקת מעוז (תקן: 1)", "ראצר סדן (תקן: 1)", "בורג עין (תקן: 1)", "פיסת אבטחה (תקן: 1)", "בוחן מעגלי ירי (תקן: 1)", "פודל (תקן: 1)", "פליז (תקן: 1)", "נגח חולץ (תקן: 1)", "גביע חליצה (תקן: 1)", "כבל הנעה (תקן: 1)", "מד מומנט (תקן: 1)", "זרקור עזר (תקן: 1)", "מברג קנ\"ר (תקן: 1)", "גק ערבי (תקן: 1)", "שוש אייל (תקן: 1)", "את חפירה (תקן: 1)", "מגרזת (תקן: 1)", "עצר לטנק (תקן: 1)", "מפתח כיס (תקן: 1)", "כיסוי תותח (תקן: 1)", "פנל זיהוי רק\"מ (תקן: 1)", "קרינור (תקן: 1)", "משמנת (תקן: 1)", "כפפות אסבסט (תקן: 1)", "פלייר (תקן: 1)", "כיסוי מאג (תקן: 1)", "כיסוי 05 (תקן: 1)", "מברשת בית בליעה (תקן: 1)", "ידית T (תקן: 1)", "ראצר 3\\4 (תקן: 1)", "ראצר חצי (תקן: 1)", "איזמל (תקן: 1)", "מברשת 4 (תקן: 1)", "שפכטל (תקן: 1)", "מגזרי תיל (תקן: 1)", "מפתח שוודי (תקן: 1)", "כיסוי תובה (תקן: לא מוגדר)", "משאבת סולר (תקן: לא מוגדר)", "מאג (תקן: 40)", "0.5 (תקן: 2)", "חלול (תקן: 10)", "חצב (תקן: 17)", "כלנית (תקן: 4)", "חץ (תקן: 3)", "רימון רסס (תקן: 4)", "מעיל רוח (תקן: 6)", "מטען ניתוק זחל (תקן: 1)", "נונל (תקן: 1)", "שרשרת גרירה (תקן: 3)", "שאקל 25 (תקן: 2)", "שאקל קרנף (תקן: 2)", "שאקל 5 (תקן: 4 פלוגתי)", "סט שיני חזיר\\נג\"ח (תקן: 1)"])
    .setColumns(["תקין", "חסר", "תקול"])
    .setRequired(true);
  form.addParagraphTextItem()
    .setTitle("פירוט חוסרים/תקלות - לוגיסטיקה")
    .setHelpText("ציין רק מה שחסר/תקול, כולל פירוט קצר לפעולה.")
    .setRequired(false);

  // --- חימוש ---
  form.addPageBreakItem().setTitle("חימוש");
  form.addGridItem()
    .setTitle("סטטוס פריטים - חימוש")
    .setRows(["מגבר 1 (תקן: 1)", "מגבר 2 (תקן: לא מוגדר)", "מגבר 3 (תקן: לא מוגדר)"])
    .setColumns(["תקין", "חסר", "תקול"])
    .setRequired(true);
  form.addParagraphTextItem()
    .setTitle("פירוט חוסרים/תקלות - חימוש")
    .setHelpText("ציין רק מה שחסר/תקול, כולל פירוט קצר לפעולה.")
    .setRequired(false);

  // --- תקשוב ---
  form.addPageBreakItem().setTitle("תקשוב");
  form.addGridItem()
    .setTitle("סטטוס פריטים - תקשוב")
    .setRows(["מקמש (תקן: 1)", "גנטקס (תקן: 5)", "פתיל (תקן: 5)", "מעד (תקן: 1)", "מיק חירום (תקן: 1)", "רמק (תקן: 1)", "מכלול (תקן: 1)", "נר לילה (תקן: 587009)", "מבן (תקן: לא מוגדר)", "אנטנת מבן (תקן: לא מוגדר)", "2 שייקספיר (תקן: 2)", "מעד (תקן: 1)", "קפ שליטה (תקן: 1)", "רמק (תקן: 1)", "משיב מיקום (תקן: 563365)", "NFC (תקן: לא מוגדר)", "מחשב 1 (תקן: 1)", "מחשב 2 (תקן: 1)", "מחשב 3 (תקן: לא מוגדר)", "מסך 1 (תקן: 1)", "מסך 2 (תקן: 1)", "מסך 3 (תקן: 1)", "מקלדת 1 (תקן: 1)", "מקלדת 2 (תקן: 1)", "מקלדת 3 (תקן: 1)", "עכבר 1 (תקן: 1)", "עכבר 2 (תקן: 1)", "עכבר 3 (תקן: 1)", "מדפסת (תקן: 1)", "מאג 1 (תקן: לא מוגדר)", "מאג 2 (תקן: לא מוגדר)", "מקלע 05 (תקן: לא מוגדר)", "אמרל (תקן: לא מוגדר)", "משקפת (תקן: לא מוגדר)", "מצפן (תקן: לא מוגדר)", "אולר (תקן: לא מוגדר)", "בורוסייט (תקן: לא מוגדר)", "NFC (תקן: לא מוגדר)", "מדיה\\נר לילה (תקן: לא מוגדר)", "סלולר (תקן: לא מוגדר)", "מבן (תקן: לא מוגדר)", "מקמש\\מגן מכלול (תקן: לא מוגדר)", "אלעד ירוק (תקן: לא מוגדר)"])
    .setColumns(["תקין", "חסר", "תקול"])
    .setRequired(true);
  form.addParagraphTextItem()
    .setTitle("פירוט חוסרים/תקלות - תקשוב")
    .setHelpText("ציין רק מה שחסר/תקול, כולל פירוט קצר לפעולה.")
    .setRequired(false);

  form.addParagraphTextItem().setTitle("הערות לסיכום");
  Logger.log("Tank form edit URL: " + form.getEditUrl());
  Logger.log("Tank form published URL: " + form.getPublishedUrl());
}

function createSpearheadCompanyAssetsForm() {
  const form = FormApp.create("קצה הרומח | דוח ציוד פלוגתי שבועי");
  form.setDescription("טופס שבועי לעוזר מ\"פ עבור ציוד פלוגתי. לדווח תקין/חסר/תקול ולפרט רק חריגים.");
  form.setCollectEmail(true);
  form.setAllowResponseEdits(true);

  form.addListItem()
    .setTitle("פלוגה")
    .setChoiceValues(["כפיר", "מחץ", "סופה"])
    .setRequired(true);
  form.addDateItem().setTitle("תאריך דיווח").setRequired(true);
  form.addTextItem().setTitle("שם מדווח").setRequired(true);

  // --- חלפים (ח"ח פלוגתי) ---
  form.addPageBreakItem().setTitle("חלפים (ח\"ח פלוגתי)");
  form.addGridItem()
    .setTitle("סטטוס פריטים - חלפים (ח\"ח פלוגתי)")
    .setRows(["ח\"ח פלוגתי", "חוליות אקסטרה פלוגתי", "פינים אקסטרה פלוגתי"])
    .setColumns(["תקין", "חסר", "תקול"])
    .setRequired(true);
  form.addParagraphTextItem()
    .setTitle("פירוט חריגים - חלפים (ח\"ח פלוגתי)")
    .setRequired(false);

  // --- שמנים וחומרי סיכה ---
  form.addPageBreakItem().setTitle("שמנים וחומרי סיכה");
  form.addGridItem()
    .setTitle("סטטוס פריטים - שמנים וחומרי סיכה")
    .setRows(["2510 אקסטרה פלוגתי (תקן: 1)", "2640 אקסטרה פלוגתי (תקן: 1)", "גריז 2040 פלוגתי (תקן: 1)", "גריז 4080 פלוגתי (תקן: 1)"])
    .setColumns(["תקין", "חסר", "תקול"])
    .setRequired(true);
  form.addParagraphTextItem()
    .setTitle("פירוט חריגים - שמנים וחומרי סיכה")
    .setRequired(false);

  // --- דוחות ותוספות פלוגתיות ---
  form.addPageBreakItem().setTitle("דוחות ותוספות פלוגתיות");
  form.addGridItem()
    .setTitle("סטטוס פריטים - דוחות ותוספות פלוגתיות")
    .setRows(["דוח צלם- נוספים", "דוח ת\"ת פלוגתי", "ציוד רנגלר", "ציוד קשפל"])
    .setColumns(["תקין", "חסר", "תקול"])
    .setRequired(true);
  form.addParagraphTextItem()
    .setTitle("פירוט חריגים - דוחות ותוספות פלוגתיות")
    .setRequired(false);

  form.addParagraphTextItem().setTitle("הערות לסיכום");
  Logger.log("Company assets form edit URL: " + form.getEditUrl());
  Logger.log("Company assets form published URL: " + form.getPublishedUrl());
}
