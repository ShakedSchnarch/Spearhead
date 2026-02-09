from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class FormEventV2(BaseModel):
    schema_version: str = Field(default="v2", min_length=1)
    source_id: Optional[str] = None
    received_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any] = Field(default_factory=dict)
    event_id: Optional[str] = None

    @field_validator("received_at", mode="before")
    @classmethod
    def _coerce_received_at(cls, value: Any) -> datetime:
        if value is None:
            return datetime.now(UTC)
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=UTC)
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


class NormalizedResponseV2(BaseModel):
    event_id: str
    source_id: Optional[str] = None
    platoon_key: str
    tank_id: str
    week_id: str
    received_at: datetime
    fields: dict[str, Any] = Field(default_factory=dict)
    unmapped_fields: list[str] = Field(default_factory=list)


class MetricSnapshotV2(BaseModel):
    scope: Literal["overview", "platoon", "tank"]
    dimensions: dict[str, str] = Field(default_factory=dict)
    values: dict[str, Any] = Field(default_factory=dict)
    computed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class UserScope(BaseModel):
    role: Literal["battalion", "platoon"] = "battalion"
    platoon_scope: Optional[str] = None

    @property
    def is_restricted(self) -> bool:
        return self.role == "platoon" and bool(self.platoon_scope)


class IngestionReportV2(BaseModel):
    event_id: str
    created: bool
    schema_version: str
    source_id: Optional[str] = None
    week_id: Optional[str] = None
    platoon_key: Optional[str] = None
    unmapped_fields: list[str] = Field(default_factory=list)
