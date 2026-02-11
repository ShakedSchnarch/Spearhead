#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_SOURCE = Path("data/kfir_week7_form_schema.json")
DEFAULT_OUTPUT = Path("docs/forms/kfir_company_form_blueprint.json")

# This mapping stays explicit and easy to update once the final approved list arrives.
FAMILY_TO_OPERATIONAL_SECTION = {
    "zivud": "Logistics",
    "ammo": "Logistics",
    "kashpal": "Armament",
    "communications_core": "Communications",
    "ranger": "Communications",
    "device_issue_matrix": "Communications",
    "office": "Communications",
}

STATUS_CHOICES = ["תקין", "חסר", "תקול"]
REQUIRES_NOTE_FOR = ["חסר", "תקול"]


@dataclass
class FormItem:
    operational_section: str
    family: str
    item: str
    standard: Any
    index: int

    def to_question(self) -> dict[str, Any]:
        return {
            "id": f"{self.operational_section.lower()}.{self.family}.{self.index:03d}",
            "section": self.operational_section,
            "family": self.family,
            "label_he": self.item,
            "standard": self.standard,
            "response_type": "status_with_note",
            "choices": STATUS_CHOICES,
            "requires_note_for": REQUIRES_NOTE_FOR,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate modular Kfir form blueprint from existing schema snapshot.")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE), help="Path to source schema JSON")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Path to output blueprint JSON")
    parser.add_argument("--company", default="כפיר", help="Company label in Hebrew")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_path = Path(args.source)
    output_path = Path(args.output)

    if not source_path.exists():
        raise SystemExit(f"Source file not found: {source_path}")

    payload = json.loads(source_path.read_text(encoding="utf-8"))
    sections: dict[str, list[dict[str, Any]]] = payload.get("sections", {})

    grouped: dict[str, list[dict[str, Any]]] = {
        "Logistics": [],
        "Armament": [],
        "Communications": [],
    }
    unmapped_families: list[str] = []

    for family, rows in sections.items():
        operational = FAMILY_TO_OPERATIONAL_SECTION.get(family)
        if not operational:
            unmapped_families.append(family)
            continue
        for idx, row in enumerate(rows, start=1):
            if isinstance(row, dict):
                item = str(row.get("item", "")).strip()
                standard = row.get("standard")
            else:
                item = str(row).strip()
                standard = None
            grouped[operational].append(
                FormItem(
                    operational_section=operational,
                    family=family,
                    item=item,
                    standard=standard,
                    index=idx,
                ).to_question()
            )

    output = {
        "version": "draft-v1",
        "company": args.company,
        "source_file": str(source_path),
        "response_format": {
            "type": "status_with_note",
            "choices": STATUS_CHOICES,
            "requires_note_for": REQUIRES_NOTE_FOR,
        },
        "sections": grouped,
        "counts": {key: len(value) for key, value in grouped.items()},
        "unmapped_families": unmapped_families,
        "notes": [
            "Armament mapping is draft and must be finalized by domain approval.",
            "This blueprint is intended for Google Forms generation and backend field mapping alignment.",
        ],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote blueprint: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
