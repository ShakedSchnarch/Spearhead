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
    row_index: int
    tank_id: Optional[str]
    timestamp: Optional[datetime]
    fields: Dict[str, Any]
