#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml


DEFAULT_BLUEPRINT = Path("docs/forms/kfir_company_form_blueprint.json")
DEFAULT_TANKS = Path("docs/forms/kfir_tank_ids.json")
DEFAULT_OUTPUT = Path("docs/forms/kfir_google_form_apps_script.gs")
DEFAULT_STANDARDS = Path("config/operational_standards.yaml")
DEFAULT_TANK_IDS = ["צ׳329", "צ׳337", "צ׳423", "צ׳427", "צ׳456", "צ׳631", "צ׳636", "צ׳637", "צ׳653", "צ׳670", "צ׳676"]
DEFAULT_COMPANIES = ["כפיר", "מחץ", "סופה"]
STATUS_CHOICES = ["תקין", "חסר", "תקול"]

COMPANY_LABELS_FALLBACK = {
    "Kfir": "כפיר",
    "Mahatz": "מחץ",
    "Sufa": "סופה",
    "Palsam": "פלס״מ",
}

SECTION_TITLES = {
    "Logistics": "לוגיסטיקה",
    "Armament": "חימוש",
    "Communications": "תקשוב",
}

FALLBACK_COMPANY_ASSET_GROUPS = [
    {
        "title": 'חלפים (ח"ח פלוגתי)',
        "rows": ['ח"ח פלוגתי', "חוליות אקסטרה פלוגתי", "פינים אקסטרה פלוגתי"],
    },
    {
        "title": "שמנים וחומרי סיכה",
        "rows": [
            "2510 אקסטרה פלוגתי",
            "2640 אקסטרה פלוגתי",
            "גריז 2040 פלוגתי",
            "גריז 4080 פלוגתי",
        ],
    },
    {
        "title": 'צלם ות"ת פלוגתי',
        "rows": ["דוח צלם- נוספים", 'דוח ת"ת פלוגתי', "ציוד רנגלר", "ציוד קשפל"],
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate production-grade Google Apps Script for Spearhead forms.")
    parser.add_argument("--blueprint", default=str(DEFAULT_BLUEPRINT), help="Blueprint JSON path")
    parser.add_argument("--tank-ids", default=str(DEFAULT_TANKS), help="Tank IDs JSON path")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output .gs script path")
    parser.add_argument("--standards", default=str(DEFAULT_STANDARDS), help="Operational standards YAML path")
    parser.add_argument("--tank-form-title", default="קצה הרומח | דוח מפקד טנק שבועי", help="Tank form title")
    parser.add_argument("--assets-form-title", default="קצה הרומח | דוח ציוד פלוגתי שבועי", help="Company assets form title")
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


def format_label_with_standard(item_name: str, standard: Any) -> str:
    if standard is None:
        return item_name
    return f"{item_name} (תקן: {format_standard(standard)})"


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


def load_standards(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return loaded if isinstance(loaded, dict) else {}


def resolve_companies(standards: dict[str, Any]) -> list[str]:
    active = standards.get("active_companies", [])
    labels = standards.get("company_labels", {})
    if not isinstance(active, list):
        return DEFAULT_COMPANIES
    values = []
    for company in active:
        key = str(company).strip()
        if not key:
            continue
        label = None
        if isinstance(labels, dict):
            label = labels.get(key)
        label = label or COMPANY_LABELS_FALLBACK.get(key) or key
        values.append(str(label))
    return values or DEFAULT_COMPANIES


def resolve_company_asset_groups(standards: dict[str, Any]) -> list[dict[str, Any]]:
    groups = standards.get("company_assets", {}).get("groups", [])
    if not isinstance(groups, list) or not groups:
        return FALLBACK_COMPANY_ASSET_GROUPS

    resolved: list[dict[str, Any]] = []
    for group in groups:
        if not isinstance(group, dict):
            continue
        title = str(group.get("title") or group.get("group") or "").strip()
        items = group.get("items", [])
        if not title or not isinstance(items, list):
            continue
        rows = []
        for item in items:
            if isinstance(item, str):
                rows.append(item)
                continue
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or item.get("item") or "").strip()
            if not name:
                continue
            rows.append(format_label_with_standard(name, item.get("standard_quantity")))
        if rows:
            resolved.append({"title": title, "rows": rows})
    return resolved or FALLBACK_COMPANY_ASSET_GROUPS


def build_script(
    *,
    tank_form_title: str,
    assets_form_title: str,
    blueprint: dict[str, Any],
    tank_ids: list[str],
    companies: list[str],
    company_asset_groups: list[dict[str, Any]],
) -> str:
    sections = blueprint.get("sections", {})
    lines: list[str] = []

    lines.append("function createSpearheadForms() {")
    lines.append("  createSpearheadTankCommanderForm();")
    lines.append("  createSpearheadCompanyAssetsForm();")
    lines.append("}")
    lines.append("")

    lines.append("function createSpearheadTankCommanderForm() {")
    lines.append(f"  const form = FormApp.create({quote(tank_form_title)});")
    lines.append(
        "  form.setDescription(" + quote(
            "טופס שבועי למפקד טנק. מילוי ברור, קצר ועקבי: תקין / חסר / תקול + פירוט תקלות לפי צורך."
        ) + ");"
    )
    lines.append("  form.setCollectEmail(true);")
    lines.append("  form.setAllowResponseEdits(true);")
    lines.append("")

    lines.append("  form.addListItem()")
    lines.append("    .setTitle(" + quote("פלוגה") + ")")
    lines.append("    .setChoiceValues([" + ", ".join(quote(value) for value in companies) + "])")
    lines.append("    .setRequired(true);")
    lines.append("  form.addListItem()")
    lines.append("    .setTitle(" + quote("מספר טנק") + ")")
    lines.append("    .setChoiceValues([" + ", ".join(quote(tank) for tank in tank_ids) + "])")
    lines.append("    .setRequired(true);")
    lines.append("  form.addDateItem().setTitle(" + quote("תאריך דיווח") + ").setRequired(true);")
    lines.append("  form.addTextItem().setTitle(" + quote("שם מדווח") + ").setRequired(true);")
    lines.append("  form.addParagraphTextItem().setTitle(" + quote("הערת פתיחה (אופציונלי)") + ");")
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
        lines.append("    .setTitle(" + quote(f"סטטוס פריטים - {section_title}") + ")")
        lines.append("    .setRows([" + ", ".join(quote(label) for label in labels) + "])")
        lines.append("    .setColumns([" + ", ".join(quote(choice) for choice in STATUS_CHOICES) + "])")
        lines.append("    .setRequired(true);")
        lines.append("  form.addParagraphTextItem()")
        lines.append("    .setTitle(" + quote(f"פירוט חוסרים/תקלות - {section_title}") + ")")
        lines.append("    .setHelpText(" + quote("ציין רק מה שחסר/תקול, כולל פירוט קצר לפעולה.") + ")")
        lines.append("    .setRequired(false);")
        lines.append("")

    lines.append("  form.addParagraphTextItem().setTitle(" + quote("הערות לסיכום") + ");")
    lines.append('  Logger.log("Tank form edit URL: " + form.getEditUrl());')
    lines.append('  Logger.log("Tank form published URL: " + form.getPublishedUrl());')
    lines.append("}")
    lines.append("")

    lines.append("function createSpearheadCompanyAssetsForm() {")
    lines.append(f"  const form = FormApp.create({quote(assets_form_title)});")
    lines.append(
        "  form.setDescription(" + quote(
            "טופס שבועי לעוזר מ\"פ עבור ציוד פלוגתי. לדווח תקין/חסר/תקול ולפרט רק חריגים."
        ) + ");"
    )
    lines.append("  form.setCollectEmail(true);")
    lines.append("  form.setAllowResponseEdits(true);")
    lines.append("")
    lines.append("  form.addListItem()")
    lines.append("    .setTitle(" + quote("פלוגה") + ")")
    lines.append("    .setChoiceValues([" + ", ".join(quote(value) for value in companies) + "])")
    lines.append("    .setRequired(true);")
    lines.append("  form.addDateItem().setTitle(" + quote("תאריך דיווח") + ").setRequired(true);")
    lines.append("  form.addTextItem().setTitle(" + quote("שם מדווח") + ").setRequired(true);")
    lines.append("")

    for group in company_asset_groups:
        title = group["title"]
        rows = group["rows"]
        lines.append(f"  // --- {title} ---")
        lines.append("  form.addPageBreakItem().setTitle(" + quote(title) + ");")
        lines.append("  form.addGridItem()")
        lines.append("    .setTitle(" + quote(f"סטטוס פריטים - {title}") + ")")
        lines.append("    .setRows([" + ", ".join(quote(item) for item in rows) + "])")
        lines.append("    .setColumns([" + ", ".join(quote(choice) for choice in STATUS_CHOICES) + "])")
        lines.append("    .setRequired(true);")
        lines.append("  form.addParagraphTextItem()")
        lines.append("    .setTitle(" + quote(f"פירוט חריגים - {title}") + ")")
        lines.append("    .setRequired(false);")
        lines.append("")

    lines.append("  form.addParagraphTextItem().setTitle(" + quote("הערות לסיכום") + ");")
    lines.append('  Logger.log("Company assets form edit URL: " + form.getEditUrl());')
    lines.append('  Logger.log("Company assets form published URL: " + form.getPublishedUrl());')
    lines.append("}")

    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    blueprint_path = Path(args.blueprint)
    tanks_path = Path(args.tank_ids)
    output_path = Path(args.output)
    standards_path = Path(args.standards)

    if not blueprint_path.exists():
        raise SystemExit(f"Blueprint not found: {blueprint_path}")

    blueprint = json.loads(blueprint_path.read_text(encoding="utf-8"))
    standards = load_standards(standards_path)
    tank_ids = load_tanks(tanks_path)
    companies = resolve_companies(standards)
    company_asset_groups = resolve_company_asset_groups(standards)

    script = build_script(
        tank_form_title=args.tank_form_title,
        assets_form_title=args.assets_form_title,
        blueprint=blueprint,
        tank_ids=tank_ids,
        companies=companies,
        company_asset_groups=company_asset_groups,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(script, encoding="utf-8")
    print(f"Wrote Apps Script: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
