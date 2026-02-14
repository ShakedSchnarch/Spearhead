from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

_DEFAULT_ACTIVE_COMPANIES = ["Kfir", "Mahatz", "Sufa"]
_DEFAULT_COMPANY_LABELS = {
    "Kfir": "כפיר",
    "Mahatz": "מחץ",
    "Sufa": "סופה",
    "Palsam": "פלס״מ",
}
_DEFAULT_CRITICAL_ITEMS = [
    "חבל פריסה",
    "פטיש 5",
    "ראשוני",
    "איציק",
    "לום",
    'מאריך חש"ן',
    "בייבי קוני",
    "משלק",
    "פטיש קילו",
    "מפתח Y",
    "2מפתח פלטות",
    "בוקסה 1\\5\\16",
    "ידית כוח חצי",
    "ידית כוח 3\\4",
    "מחט ירי",
    "אלונקה",
    "מקלות חוטר",
]


def _normalize_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    replacements = {
        "׳": "",
        "״": "",
        '"': "",
        "'": "",
        "\\": "",
        "/": "",
        "-": "",
        "_": "",
        ".": "",
        ",": "",
        " ": "",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def _canonical_company_key(value: Any) -> str:
    token = _normalize_text(value)
    aliases = {
        "כפיר": "Kfir",
        "kfir": "Kfir",
        "kphir": "Kfir",
        "מחץ": "Mahatz",
        "mahatz": "Mahatz",
        "machatz": "Mahatz",
        "סופה": "Sufa",
        "sufa": "Sufa",
        "פלסמ": "Palsam",
        "פלסם": "Palsam",
        "palsam": "Palsam",
    }
    return aliases.get(token, str(value or "").strip())


@dataclass(slots=True)
class CompanyAssetStandard:
    name: str
    section: str
    group: str
    is_critical: bool = False
    has_category_code: bool = False
    standard_quantity: Any = None
    aliases: list[str] = field(default_factory=list)

    @property
    def normalized_name(self) -> str:
        return _normalize_text(self.name)

    @property
    def normalized_aliases(self) -> list[str]:
        return [_normalize_text(alias) for alias in self.aliases if _normalize_text(alias)]

    def matches(self, item_name: str, field_name: str = "") -> bool:
        item_key = _normalize_text(item_name)
        field_key = _normalize_text(field_name)
        keys = [self.normalized_name, *self.normalized_aliases]
        if item_key and item_key in keys:
            return True
        for key in keys:
            if key and ((item_key and key in item_key) or (field_key and key in field_key)):
                return True
        return False


@dataclass(slots=True)
class OperationalStandards:
    version: str = "default"
    active_companies: list[str] = field(default_factory=lambda: list(_DEFAULT_ACTIVE_COMPANIES))
    company_labels: dict[str, str] = field(default_factory=lambda: dict(_DEFAULT_COMPANY_LABELS))
    critical_items: list[str] = field(default_factory=lambda: list(_DEFAULT_CRITICAL_ITEMS))
    tank_item_standards: dict[str, Any] = field(default_factory=dict)
    company_asset_items: list[CompanyAssetStandard] = field(default_factory=list)

    def tank_standard_for_item(self, item_name: str) -> Any:
        if not item_name:
            return None
        return self.tank_item_standards.get(_normalize_text(item_name))

    def find_company_asset(self, *, item_name: str, field_name: str = "") -> Optional[CompanyAssetStandard]:
        for entry in self.company_asset_items:
            if entry.matches(item_name, field_name):
                return entry
        return None


def _load_tank_item_standards(blueprint_path: Optional[Path]) -> dict[str, Any]:
    if not blueprint_path:
        return {}
    if not blueprint_path.exists():
        return {}
    try:
        payload = json.loads(blueprint_path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    sections = payload.get("sections", {})
    standards: dict[str, Any] = {}
    for rows in sections.values():
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            item_name = str(row.get("label_he") or row.get("item") or "").strip()
            if not item_name:
                continue
            standards[_normalize_text(item_name)] = row.get("standard")
    return standards


def _resolve_optional_path(value: Any, *, config_path: Path) -> Optional[Path]:
    if not value:
        return None
    raw = Path(str(value))
    if raw.is_absolute():
        return raw
    config_relative = (config_path.parent / raw).resolve()
    if config_relative.exists():
        return config_relative
    cwd_relative = (Path.cwd() / raw).resolve()
    if cwd_relative.exists():
        return cwd_relative
    # Return the best candidate even if not found; caller handles existence.
    return cwd_relative


def _load_company_asset_items(payload: dict[str, Any]) -> list[CompanyAssetStandard]:
    groups = payload.get("company_assets", {}).get("groups", [])
    if not isinstance(groups, list):
        return []

    rows: list[CompanyAssetStandard] = []
    for group_payload in groups:
        if not isinstance(group_payload, dict):
            continue
        section = str(group_payload.get("section") or "Company Assets").strip() or "Company Assets"
        group = str(group_payload.get("group") or group_payload.get("title") or "כללי").strip() or "כללי"
        items = group_payload.get("items", [])
        if not isinstance(items, list):
            continue
        for item_payload in items:
            if isinstance(item_payload, str):
                item_payload = {"name": item_payload}
            if not isinstance(item_payload, dict):
                continue
            name = str(item_payload.get("name") or item_payload.get("item") or "").strip()
            if not name:
                continue
            aliases = item_payload.get("aliases", [])
            rows.append(
                CompanyAssetStandard(
                    name=name,
                    section=section,
                    group=group,
                    is_critical=bool(item_payload.get("critical", False)),
                    has_category_code=bool(item_payload.get("has_category_code", False)),
                    standard_quantity=item_payload.get("standard_quantity"),
                    aliases=[str(alias) for alias in aliases] if isinstance(aliases, list) else [],
                )
            )
    return rows


def _default_standards() -> OperationalStandards:
    return OperationalStandards()


def load_operational_standards(path: Optional[Path]) -> OperationalStandards:
    if not path:
        return _default_standards()
    if not path.exists():
        return _default_standards()

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return _default_standards()

    version = str(payload.get("version") or "default")
    raw_companies = payload.get("active_companies", [])
    active_companies = []
    if isinstance(raw_companies, list):
        for company in raw_companies:
            canonical = _canonical_company_key(company)
            if canonical and canonical not in active_companies:
                active_companies.append(canonical)
    if not active_companies:
        active_companies = list(_DEFAULT_ACTIVE_COMPANIES)

    labels = dict(_DEFAULT_COMPANY_LABELS)
    raw_labels = payload.get("company_labels", {})
    if isinstance(raw_labels, dict):
        for key, value in raw_labels.items():
            canonical = _canonical_company_key(key)
            if canonical:
                labels[canonical] = str(value)

    raw_critical_items = payload.get("critical_items", [])
    critical_items = [str(item).strip() for item in raw_critical_items if str(item).strip()]
    if not critical_items:
        critical_items = list(_DEFAULT_CRITICAL_ITEMS)

    blueprint_path = _resolve_optional_path(payload.get("tank_blueprint_path"), config_path=path)
    tank_item_standards = _load_tank_item_standards(blueprint_path)
    company_asset_items = _load_company_asset_items(payload)

    return OperationalStandards(
        version=version,
        active_companies=active_companies,
        company_labels=labels,
        critical_items=critical_items,
        tank_item_standards=tank_item_standards,
        company_asset_items=company_asset_items,
    )
