import logging
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from iron_view.config_fields import FieldConfig, field_config, FamilyConfig

logger = logging.getLogger(__name__)


@dataclass
class HeaderMatch:
    raw: str
    normalized: str
    family: str
    item: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "raw": self.raw,
            "normalized": self.normalized,
            "family": self.family,
            "item": self.item,
        }


@dataclass
class SchemaSnapshot:
    config_version: Optional[str]
    raw_headers: List[str]
    mapped: List[HeaderMatch]
    unmapped: List[str]
    missing_required: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_version": self.config_version,
            "raw_headers": self.raw_headers,
            "mapped": [m.to_dict() for m in self.mapped],
            "unmapped": self.unmapped,
            "missing_required": self.missing_required,
        }


@dataclass
class _HeaderRule:
    family: str
    regex: re.Pattern
    capture: bool
    default_item: Optional[str] = None

    def match(self, normalized_header: str) -> Optional[str]:
        m = self.regex.match(normalized_header)
        if not m:
            return None
        if self.capture:
            # First capture group wins
            for val in m.groups():
                if val:
                    return val
            return None
        return self.default_item


class FieldMapper:
    """
    Config-driven resolver for headers and row-level fields.
    Handles slugging (punctuation/diacritics), wildcard alias matching, and platoon inference.
    """

    def __init__(self, config: FieldConfig = field_config):
        self.config = config
        self.rules: List[_HeaderRule] = self._build_rules()
        self._tank_aliases = {self.normalize(a) for a in self.config.form.tank_id.aliases}
        self._timestamp_aliases = {self.normalize(a) for a in self.config.form.timestamp.aliases}
        self._commander_aliases = {self.normalize(a) for a in self.config.form.commander.aliases}

    @staticmethod
    def normalize(text: Optional[str]) -> str:
        if text is None:
            return ""
        normalized = unicodedata.normalize("NFKD", str(text))
        normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
        normalized = normalized.lower()
        normalized = re.sub(r"[^\w\s]", " ", normalized, flags=re.UNICODE)
        normalized = normalized.replace("_", " ")
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    def clean_item(self, text: Optional[str]) -> str:
        if text is None:
            return ""
        normalized = unicodedata.normalize("NFKD", str(text))
        normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
        normalized = re.sub(r"[^\w\s]", " ", normalized, flags=re.UNICODE)
        normalized = normalized.replace("_", " ")
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    def snapshot(self, headers: Iterable[Any]) -> SchemaSnapshot:
        mapped: List[HeaderMatch] = []
        unmapped: List[str] = []
        normalized_headers = set()

        for raw in headers:
            if raw is None:
                continue
            raw_str = str(raw).strip()
            if not raw_str:
                continue
            normalized = self.normalize(raw_str)
            normalized_headers.add(normalized)
            match = self.match_header(raw_str)
            if match:
                mapped.append(match)
            else:
                unmapped.append(raw_str)

        missing_required = self._missing_required(normalized_headers)
        return SchemaSnapshot(
            config_version=getattr(self.config, "version", None),
            raw_headers=[str(h) for h in headers if h],
            mapped=mapped,
            unmapped=unmapped,
            missing_required=missing_required,
        )

    def match_header(self, header: str) -> Optional[HeaderMatch]:
        normalized = self.normalize(header)
        for rule in self.rules:
            item_raw = rule.match(normalized)
            if item_raw is None:
                continue
            item = self.clean_item(item_raw if rule.capture else (rule.default_item or header))
            return HeaderMatch(raw=header, normalized=normalized, family=rule.family, item=item)
        return None

    def infer_platoon(self, file_path: Path, source_id: Optional[str] = None) -> Optional[str]:
        if source_id:
            platoon = self.config.form.platoon_inference.sheet_ids.get(source_id)
            if platoon:
                return platoon

        stem_norm = self.normalize(file_path.stem)
        for rule in self.config.form.platoon_inference.file_names:
            match_token = rule.get("match")
            platoon_name = rule.get("platoon")
            if match_token and platoon_name:
                if self.normalize(match_token) in stem_norm:
                    return platoon_name

        # Fallback: last token from the file name
        tokens = [t for t in re.split(r"[\\s_\\-]+", file_path.stem) if t]
        if tokens:
            return tokens[-1]
        return None

    def extract_by_aliases(self, row: Dict[str, Any], aliases: Iterable[str]) -> Optional[Any]:
        normalized_row = {self.normalize(k): v for k, v in row.items() if k}
        alias_norms = {self.normalize(a) for a in aliases}
        for key, value in normalized_row.items():
            if key in alias_norms:
                return value
        return None

    def extract_tank_id(self, row: Dict[str, Any]) -> Optional[str]:
        val = self.extract_by_aliases(row, self.config.form.tank_id.aliases)
        if val is None:
            return None
        text = str(val).strip()
        return text or None

    def extract_commander(self, row: Dict[str, Any]) -> Optional[str]:
        val = self.extract_by_aliases(row, self.config.form.commander.aliases)
        if val is None:
            return None
        text = str(val).strip()
        return text or None

    def required_present(self, normalized_headers: Iterable[str]) -> bool:
        missing = self._missing_required(set(normalized_headers))
        return len(missing) == 0

    def _missing_required(self, normalized_headers: Iterable[str]) -> List[str]:
        headers_set = set(normalized_headers)
        missing: List[str] = []
        if not headers_set.intersection(self._tank_aliases):
            missing.append("tank_id")
        if not headers_set.intersection(self._timestamp_aliases):
            missing.append("timestamp")
        return missing

    def _build_rules(self) -> List[_HeaderRule]:
        rules: List[_HeaderRule] = []
        for family, conf in self.config.form.families.items():
            rules.extend(self._rules_for_family(family, conf))
        return rules

    def _rules_for_family(self, family: str, conf: FamilyConfig) -> List[_HeaderRule]:
        rules: List[_HeaderRule] = []
        for alias in list(conf.aliases) + list(conf.extras):
            rules.append(self._build_rule(family, alias))
        return rules

    def _build_rule(self, family: str, alias: str) -> _HeaderRule:
        capture = "*" in alias
        regex = self._compile_pattern(alias)
        default_item = None if capture else self.clean_item(alias)
        return _HeaderRule(family=family, regex=regex, capture=capture, default_item=default_item)

    def _compile_pattern(self, alias: str) -> re.Pattern:
        placeholder = "__WILDCARD__"
        normalized = self.normalize(alias.replace("*", placeholder))
        placeholder_norm = self.normalize(placeholder)
        parts = normalized.split(placeholder_norm)
        regex_parts: List[str] = []

        for i, part in enumerate(parts):
            part = part.strip()
            if part:
                regex_parts.append(re.escape(part))
            if i < len(parts) - 1:
                regex_parts.append(r"(.+?)")

        body = r"\s*".join(regex_parts)
        allow_trailing = bool(parts and parts[-1].strip())
        tail = r"(?:\s+.*)?$" if allow_trailing else r"(?:\s*)$"
        return re.compile(rf"^{body}{tail}", flags=re.IGNORECASE)
