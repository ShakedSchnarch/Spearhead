from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from spearhead.data.field_mapper import FieldMapper
from spearhead.v1.models import (
    CompanyAssetEventV2,
    FormEventV2,
    NormalizedCompanyAssetV2,
    NormalizedResponseV2,
)


class EventValidationError(ValueError):
    def __init__(self, message: str, *, unmapped_fields: list[str] | None = None):
        super().__init__(message)
        self.unmapped_fields = unmapped_fields or []


class FormResponseParserV2:
    """
    Parser for JSON form events.
    Uses existing FieldMapper rules and enforces strict required columns.
    """

    def __init__(self, mapper: FieldMapper | None = None):
        self.mapper = mapper or FieldMapper()

    def parse(self, event: FormEventV2) -> NormalizedResponseV2:
        if not isinstance(event.payload, dict) or not event.payload:
            raise EventValidationError("payload חייב להיות אובייקט JSON לא ריק")

        payload = self._normalize_payload(event.payload)
        snapshot = self.mapper.snapshot(payload.keys())
        if snapshot.missing_required:
            missing = ", ".join(snapshot.missing_required)
            raise EventValidationError(
                f"Missing required fields: {missing}",
                unmapped_fields=snapshot.unmapped,
            )

        tank_id = self.mapper.extract_tank_id(payload)
        if not tank_id:
            raise EventValidationError("לא נמצא מזהה טנק בשדות payload", unmapped_fields=snapshot.unmapped)

        timestamp_val = self.mapper.extract_by_aliases(payload, self.mapper.config.form.timestamp.aliases)
        received_at = self._parse_timestamp(timestamp_val) or event.received_at
        week_id = self._week_label(received_at)

        platoon_key = self._extract_platoon(payload, event)

        return NormalizedResponseV2(
            event_id=event.event_id or "",
            source_id=event.source_id,
            platoon_key=platoon_key,
            tank_id=str(tank_id).strip(),
            week_id=week_id,
            received_at=received_at,
            fields=payload,
            unmapped_fields=snapshot.unmapped,
        )

    @staticmethod
    def _normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
        clean: dict[str, Any] = {}
        for key, value in payload.items():
            if key is None:
                continue
            text_key = str(key).strip()
            if not text_key:
                continue
            if isinstance(value, (str, int, float, bool)) or value is None:
                clean[text_key] = value
            elif hasattr(value, "isoformat"):
                clean[text_key] = value.isoformat()
            else:
                clean[text_key] = str(value)
        return clean

    def _extract_platoon(self, payload: dict[str, Any], event: FormEventV2) -> str:
        candidates = [
            payload.get("פלוגה"),
            payload.get("מחלקה"),
            payload.get("platoon"),
            payload.get("company"),
            payload.get("unit"),
        ]
        for value in candidates:
            normalized = self._normalize_platoon(value)
            if normalized:
                return normalized

        inferred = self.mapper.infer_platoon(Path(event.source_id or "unknown"), source_id=event.source_id)
        if inferred:
            return inferred
        return "Unknown"

    @staticmethod
    def _normalize_platoon(name: Any) -> str | None:
        if name is None:
            return None
        raw = str(name).strip()
        if not raw:
            return None
        lower = raw.lower()
        mapping = {
            "כפיר": "Kfir",
            "kfir": "Kfir",
            "kphir": "Kfir",
            "מחץ": "Mahatz",
            "mahatz": "Mahatz",
            "machatz": "Mahatz",
            "סופה": "Sufa",
            "sufa": "Sufa",
            "פלס״מ": "Palsam",
            'פלס"ם': "Palsam",
            "פלסמ": "Palsam",
            "פלסם": "Palsam",
            "palsam": "Palsam",
            "battalion": "Battalion",
            "גדוד": "Battalion",
        }
        return mapping.get(lower, raw)

    @staticmethod
    def _parse_timestamp(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=UTC)
        try:
            if isinstance(value, (int, float)):
                base = datetime(1899, 12, 30, tzinfo=UTC)
                return base + timedelta(days=float(value))
            parsed = datetime.fromisoformat(str(value))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except Exception:
            return None

    @staticmethod
    def _week_label(ts: datetime) -> str:
        return ts.astimezone(UTC).strftime("%G-W%V")


class CompanyAssetParserV2:
    """
    Parser for company-level asset events.
    Unlike tank events, no tank-id is required. The payload is normalized into
    company/week buckets so it can be rendered in a dedicated "company assets" tab.
    """

    _COMPANY_FIELD_ALIASES = (
        "פלוגה",
        "מחלקה",
        "company",
        "platoon",
        "unit",
    )
    _TIMESTAMP_ALIASES = (
        "חותמת זמן",
        "תאריך",
        "timestamp",
        "reported_at",
    )
    _METADATA_KEYS = {
        "schema_version",
        "source_id",
        "event_id",
        "פלוגה",
        "מחלקה",
        "company",
        "platoon",
        "unit",
        "חותמת זמן",
        "תאריך",
        "timestamp",
        "reported_at",
        "שם מדווח",
        "email",
    }
    _METADATA_KEYS_LOWER = {
        "schema_version",
        "source_id",
        "event_id",
        "פלוגה",
        "מחלקה",
        "company",
        "platoon",
        "unit",
        "חותמת זמן",
        "תאריך",
        "timestamp",
        "reported_at",
        "שם מדווח",
        "email",
    }

    def __init__(self, mapper: FieldMapper | None = None):
        self.mapper = mapper or FieldMapper()

    def parse(self, event: CompanyAssetEventV2) -> NormalizedCompanyAssetV2:
        if not isinstance(event.payload, dict) or not event.payload:
            raise EventValidationError("payload חייב להיות אובייקט JSON לא ריק")

        payload = self._normalize_payload(event.payload)
        company = self._extract_company(payload, event)
        if not company:
            raise EventValidationError("לא זוהתה פלוגה באירוע ציוד פלוגתי")

        timestamp = self._extract_timestamp(payload) or event.received_at
        week_id = self._week_label(timestamp)

        fields = self._extract_fields(payload)
        if not fields:
            raise EventValidationError("לא נמצאו שדות ציוד פלוגתי באירוע")

        # Keep a lightweight unmapped list for observability.
        snapshot = self.mapper.snapshot(fields.keys())
        return NormalizedCompanyAssetV2(
            event_id=event.event_id or "",
            source_id=event.source_id,
            company_key=company,
            week_id=week_id,
            received_at=timestamp,
            fields=fields,
            unmapped_fields=snapshot.unmapped,
        )

    @staticmethod
    def _normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
        clean: dict[str, Any] = {}
        for key, value in payload.items():
            if key is None:
                continue
            text_key = str(key).strip()
            if not text_key:
                continue
            if isinstance(value, (str, int, float, bool)) or value is None:
                clean[text_key] = value
            elif hasattr(value, "isoformat"):
                clean[text_key] = value.isoformat()
            else:
                clean[text_key] = str(value)
        return clean

    def _extract_company(self, payload: dict[str, Any], event: CompanyAssetEventV2) -> str | None:
        for alias in self._COMPANY_FIELD_ALIASES:
            value = payload.get(alias)
            normalized = FormResponseParserV2._normalize_platoon(value)
            if normalized and normalized != "Battalion":
                return normalized
        inferred = self.mapper.infer_platoon(Path(event.source_id or "company-assets"), source_id=event.source_id)
        normalized_inferred = FormResponseParserV2._normalize_platoon(inferred)
        if normalized_inferred and normalized_inferred != "Battalion":
            return normalized_inferred
        return None

    @classmethod
    def _extract_fields(cls, payload: dict[str, Any]) -> dict[str, Any]:
        fields: dict[str, Any] = {}
        for key, value in payload.items():
            if key.strip().lower() in cls._METADATA_KEYS_LOWER:
                continue
            if value is None:
                continue
            text = str(value).strip()
            if not text:
                continue
            fields[key] = value
        return fields

    @classmethod
    def _extract_timestamp(cls, payload: dict[str, Any]) -> datetime | None:
        for alias in cls._TIMESTAMP_ALIASES:
            value = payload.get(alias)
            parsed = FormResponseParserV2._parse_timestamp(value)
            if parsed:
                return parsed
        return None

    @staticmethod
    def _week_label(ts: datetime) -> str:
        return ts.astimezone(UTC).strftime("%G-W%V")
