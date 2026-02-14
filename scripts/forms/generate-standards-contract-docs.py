#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _has_category_code(text: str) -> bool:
    return bool(re.search(r"צ[׳']?\s*\d{2,6}", text or ""))


def _to_company_label(standards: dict[str, Any], key: str) -> str:
    labels = standards.get("company_labels") or {}
    return str(labels.get(key) or key)


def _build_tank_rows(blueprint: dict[str, Any], critical_items: set[str]) -> list[dict[str, Any]]:
    sections = blueprint.get("sections") or {}
    rows: list[dict[str, Any]] = []
    for section_name, items in sections.items():
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label_he") or item.get("id") or "").strip()
            if not label:
                continue
            standard = item.get("standard")
            rows.append(
                {
                    "section": section_name,
                    "family": str(item.get("family") or "").strip() or "other",
                    "item": label,
                    "standard_quantity": "" if standard is None else standard,
                    "critical": "yes" if label in critical_items else "no",
                    "requires_category_code": "yes" if _has_category_code(label) else "no",
                }
            )
    rows.sort(key=lambda row: (row["section"], row["family"], row["item"]))
    return rows


def _build_company_asset_rows(standards: dict[str, Any]) -> list[dict[str, Any]]:
    groups = ((standards.get("company_assets") or {}).get("groups") or [])
    rows: list[dict[str, Any]] = []
    for group in groups:
        if not isinstance(group, dict):
            continue
        section = str(group.get("section") or "Company Assets")
        group_name = str(group.get("group") or group.get("title") or "כללי")
        for item in group.get("items") or []:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            aliases = item.get("aliases") or []
            aliases_text = ", ".join(str(alias) for alias in aliases) if isinstance(aliases, list) else ""
            rows.append(
                {
                    "section": section,
                    "group": group_name,
                    "item": name,
                    "standard_quantity": "" if item.get("standard_quantity") is None else item.get("standard_quantity"),
                    "critical": "yes" if bool(item.get("critical")) else "no",
                    "requires_category_code": "yes" if _has_category_code(name) else "no",
                    "aliases": aliases_text,
                }
            )
    rows.sort(key=lambda row: (row["section"], row["group"], row["item"]))
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _section_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counters: dict[tuple[str, str], int] = defaultdict(int)
    for row in rows:
        counters[(row["section"], row["family"])] += 1

    rendered: list[dict[str, Any]] = []
    for (section, family), count in sorted(counters.items(), key=lambda item: (item[0][0], item[0][1])):
        rendered.append({"section": section, "family": family, "items": count})
    return rendered


def _render_markdown(
    *,
    standards: dict[str, Any],
    blueprint: dict[str, Any],
    tank_rows: list[dict[str, Any]],
    company_rows: list[dict[str, Any]],
    tank_csv: Path,
    company_csv: Path,
    output_path: Path,
) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    active_companies = [str(company) for company in standards.get("active_companies") or []]
    company_labels = [_to_company_label(standards, company) for company in active_companies]
    section_summary = _section_summary(tank_rows)
    critical_items = standards.get("critical_items") or []

    lines: list[str] = []
    lines.append("# Company Equipment & Standards Contract (Commander Review)")
    lines.append("")
    lines.append(f"Updated: {today}")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append(f"- Active companies: {', '.join(company_labels) if company_labels else 'N/A'}")
    lines.append(f"- Standards version: {standards.get('version', 'N/A')}")
    lines.append(f"- Tank blueprint source: `{standards.get('tank_blueprint_path', 'N/A')}`")
    lines.append(f"- Tank contract CSV (full list): `{tank_csv}`")
    lines.append(f"- Company-assets contract CSV (full list): `{company_csv}`")
    lines.append("")
    lines.append("## Contract Notes For Approval")
    lines.append("")
    lines.append("- Baseline contract currently applies to Kfir/Mahatz/Sufa equally unless company-level deltas are approved.")
    lines.append("- Sections are fixed: `Logistics`, `Armament`, `Communications`.")
    lines.append("- Item status in forms: `תקין`, `חסר`, `תקול` (note required for `חסר`/`תקול`).")
    lines.append("- Critical items list (operational):")
    for item in critical_items:
        lines.append(f"  - {item}")
    lines.append("")

    lines.append("## Tank Equipment Breakdown By Section")
    lines.append("")
    lines.append("| Section | Family | Items |")
    lines.append("|---|---|---:|")
    for row in section_summary:
        lines.append(f"| {row['section']} | {row['family']} | {row['items']} |")
    lines.append("")

    lines.append("## Company Assets Breakdown")
    lines.append("")
    grouped_assets: dict[tuple[str, str], int] = defaultdict(int)
    for row in company_rows:
        grouped_assets[(row["section"], row["group"])] += 1
    lines.append("| Section | Group | Items |")
    lines.append("|---|---|---:|")
    for (section, group), count in sorted(grouped_assets.items(), key=lambda item: (item[0][0], item[0][1])):
        lines.append(f"| {section} | {group} | {count} |")
    lines.append("")

    lines.append("## Company-Level Review Matrix")
    lines.append("")
    lines.append("| Company | Uses Baseline Tank Contract | Uses Baseline Company-Assets Contract | Approval Status | Notes |")
    lines.append("|---|---|---|---|---|")
    for company in active_companies:
        label = _to_company_label(standards, company)
        lines.append(f"| {label} ({company}) | Yes | Yes | Pending Commander Review | |")
    lines.append("")

    lines.append("## Next Step")
    lines.append("")
    lines.append(
        "After commander approval, update any deltas directly in `config/operational_standards.yaml` and regenerate "
        "this contract before final Google Forms publication."
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    rendered = "\n".join(lines).strip() + "\n"
    output_path.write_text(rendered, encoding="utf-8")
    return rendered


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate commander-review equipment contract from standards and blueprint.")
    parser.add_argument("--standards", type=Path, default=Path("config/operational_standards.yaml"))
    parser.add_argument("--blueprint", type=Path, default=Path("docs/forms/kfir_company_form_blueprint.json"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/forms/COMPANY_EQUIPMENT_STANDARDS_CONTRACT.md"),
    )
    parser.add_argument(
        "--tank-csv",
        type=Path,
        default=Path("docs/forms/contract_tank_items.csv"),
    )
    parser.add_argument(
        "--company-csv",
        type=Path,
        default=Path("docs/forms/contract_company_assets.csv"),
    )
    args = parser.parse_args()

    standards = _load_yaml(args.standards)
    blueprint = _load_json(args.blueprint)
    critical_items = {str(item).strip() for item in standards.get("critical_items") or [] if str(item).strip()}

    tank_rows = _build_tank_rows(blueprint, critical_items)
    company_rows = _build_company_asset_rows(standards)

    _write_csv(
        args.tank_csv,
        tank_rows,
        columns=[
            "section",
            "family",
            "item",
            "standard_quantity",
            "critical",
            "requires_category_code",
        ],
    )
    _write_csv(
        args.company_csv,
        company_rows,
        columns=[
            "section",
            "group",
            "item",
            "standard_quantity",
            "critical",
            "requires_category_code",
            "aliases",
        ],
    )

    _render_markdown(
        standards=standards,
        blueprint=blueprint,
        tank_rows=tank_rows,
        company_rows=company_rows,
        tank_csv=args.tank_csv,
        company_csv=args.company_csv,
        output_path=args.output,
    )
    print(f"Generated: {args.output}")
    print(f"Generated: {args.tank_csv}")
    print(f"Generated: {args.company_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
