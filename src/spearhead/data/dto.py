from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime

from pydantic import BaseModel, Field


class TabularRecord(BaseModel):
    """
    Generic normalized cell extracted from a tabular source.
    Useful for loadout/summary sheets where headers define dimension names.
    """
    source_file: Path
    section: str
    item: str
    column: str
    value: Any
    row_index: int
    platoon: Optional[str] = Field(default=None, description="Optional platoon inferred from file name")


class FormResponseRow(BaseModel):
    """
    A single response row from the Google Form export.
    Keeps all fields for later normalization.
    """
    source_file: Path
    platoon: Optional[str]
    row_index: int
    tank_id: Optional[str]
    timestamp: Optional[datetime]
    week_label: Optional[str] = Field(default=None, description="Derived week label YYYY-Www")
    fields: Dict[str, Any]


class ReadinessStatus(BaseModel):
    """
    Summary readiness status for a unit (Tank or Platoon).
    """
    score: float = Field(..., ge=0, le=100)
    label: str = Field(..., pattern="^(GREEN|YELLOW|RED)$")
    gaps_count: int
    last_updated: datetime


class GapReport(BaseModel):
    """
    Detailed gap item for export/display.
    """
    platoon: str
    tank_id: str
    item_name: str
    gap_type: str = Field(..., description="MISSING or WEAR")
    quantity: int = 1
    week: str


class TrendPoint(BaseModel):
    """
    Single point in a readiness trend line.
    """
    week: str
    score: float
    gaps: int
