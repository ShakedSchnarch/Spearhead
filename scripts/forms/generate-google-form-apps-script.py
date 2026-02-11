#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_BLUEPRINT = Path("docs/forms/kfir_company_form_blueprint.json")
DEFAULT_TANKS = Path("docs/forms/kfir_tank_ids.json")
DEFAULT_OUTPUT = Path("docs/forms/kfir_google_form_apps_script.gs")
DEFAULT_TANK_IDS = ["צ׳329", "צ׳337", "צ׳423", "צ׳427", "צ׳456", "צ׳631", "צ׳636", "צ׳637", "צ׳653", "צ׳670", "צ׳676"]

SECTION_TITLES = {
    "Logistics": "לוגיסטיקה (מקלעים, תחמושת, זיווד)",
    "Armament": "חימוש (אמצעים, חלפים, שמנים)",
    "Communications": "תקשוב (ציוד וצופן תקלות)",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Google Apps Script draft from Spearhead form blueprint.")
    parser.add_argument("--blueprint", default=str(DEFAULT_BLUEPRINT), help="Blueprint JSON path")
    parser.add_argument("--tank-ids", default=str(DEFAULT_TANKS), help="Tank IDs JSON path")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output .gs script path")
    parser.add_argument("--form-title", default="קצה הרומח | דוח כשירות שבועי - פלוגת כפיר", help="Form title")
    return parser.parse_args()


def quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def format_standard(standard: Any) -> str:
    if standard is None:
        return "לא מוגדר"
    if isinstance(standard, float) and standard.is_integer():
        return str(int(standard))
    return str(standard)


def question_labels(rows: list[dict[str, Any]]) -> list[str]:
    labels = []
    for row in rows:
        item = str(row.get("label_he", "")).strip()
        standard = format_standard(row.get("standard"))
        labels.append(f"{item} (תקן: {standard})")
    return labels


def load_tanks(path: Path) -> list[str]:
    if not path.exists():
        return DEFAULT_TANK_IDS
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        values = [str(item) for item in payload]
        return values if values else DEFAULT_TANK_IDS
    if isinstance(payload, dict):
        values = [str(item) for item in payload.get("tanks", [])]
        return values if values else DEFAULT_TANK_IDS
    return DEFAULT_TANK_IDS


def build_script(form_title: str, blueprint: dict[str, Any], tank_ids: list[str]) -> str:
    sections = blueprint.get("sections", {})
    lines: list[str] = []

    lines.append("function createSpearheadKfirWeeklyForm() {")
    lines.append(f"  const form = FormApp.create({quote(form_title)});")
    lines.append("  form.setDescription(" + quote("דיווח שבועי למפקדי טנקים בפלוגת כפיר. פורמט תשובה קבוע: תקין/חסר/תקול.") + ");")
    lines.append("  form.setCollectEmail(true);")
    lines.append("  form.setAllowResponseEdits(true);")
    lines.append("")
    lines.append("  form.addListItem()")
    lines.append("    .setTitle(" + quote("מספר טנק") + ")")
    lines.append("    .setChoiceValues([" + ", ".join(quote(tank) for tank in tank_ids) + "])")
    lines.append("    .setRequired(true);")
    lines.append("")
    lines.append("  form.addDateItem().setTitle(" + quote("תאריך דיווח") + ").setRequired(true);")
    lines.append("  form.addTextItem().setTitle(" + quote("שם מדווח") + ").setRequired(true);")
    lines.append("  form.addParagraphTextItem().setTitle(" + quote("הערות פתיחה (אופציונלי)") + ");")
    lines.append("")

    for section_key in ["Logistics", "Armament", "Communications"]:
        rows = sections.get(section_key, [])
        if not rows:
            continue
        section_title = SECTION_TITLES.get(section_key, section_key)
        labels = question_labels(rows)

        lines.append(f"  // --- {section_title} ---")
        lines.append("  form.addPageBreakItem().setTitle(" + quote(section_title) + ");")
        lines.append("  form.addGridItem()")
        lines.append("    .setTitle(" + quote("סטטוס פריטים בתחום") + ")")
        lines.append("    .setRows([" + ", ".join(quote(label) for label in labels) + "])")
        lines.append("    .setColumns([" + ", ".join(quote(choice) for choice in ["תקין", "חסר", "תקול"]) + "])")
        lines.append("    .setRequired(true);")
        lines.append("  form.addParagraphTextItem()")
        lines.append("    .setTitle(" + quote(f"פירוט חוסרים/תקלות בתחום {section_title} (ציין פריט + פירוט קצר)") + ")")
        lines.append("    .setRequired(false);")
        lines.append("")

    lines.append("  form.addParagraphTextItem().setTitle(" + quote("הערות כלליות לסיום") + ");")
    lines.append("")
    lines.append('  Logger.log("Edit URL: " + form.getEditUrl());')
    lines.append('  Logger.log("Published URL: " + form.getPublishedUrl());')
    lines.append("}")
    lines.append("")
    lines.append("function createSpearheadCompanyAssetsFormDraft() {")
    lines.append("  const form = FormApp.create(" + quote("קצה הרומח | טופס אמצעים פלוגתיים שבועי (טיוטה)") + ");")
    lines.append("  form.setDescription(" + quote("טיוטה ראשונית לטופס עוזר מ\"פ עבור אמצעים פלוגתיים.") + ");")
    lines.append("  form.setCollectEmail(true);")
    lines.append("  form.addDateItem().setTitle(" + quote("תאריך דיווח") + ").setRequired(true);")
    lines.append("  form.addTextItem().setTitle(" + quote("שם מדווח") + ").setRequired(true);")
    lines.append("  form.addParagraphTextItem().setTitle(" + quote("רשום סטטוס אמצעים פלוגתיים (פריט: תקין/חסר/תקול + פירוט קצר)") + ");")
    lines.append('  Logger.log("Company assets form edit URL: " + form.getEditUrl());')
    lines.append("}")

    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    blueprint_path = Path(args.blueprint)
    tanks_path = Path(args.tank_ids)
    output_path = Path(args.output)

    if not blueprint_path.exists():
        raise SystemExit(f"Blueprint not found: {blueprint_path}")

    blueprint = json.loads(blueprint_path.read_text(encoding="utf-8"))
    tank_ids = load_tanks(tanks_path)

    script = build_script(args.form_title, blueprint, tank_ids)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(script, encoding="utf-8")
    print(f"Wrote Apps Script draft: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
