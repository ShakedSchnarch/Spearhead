from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class ImportRecord:
    id: int
    import_key: str
    source_file: Path
    source_type: str
    created_at: datetime


@dataclass
class TabularRowRecord:
    import_id: int
    section: str
    item: str
    column: str
    value_text: Optional[str]
    value_num: Optional[float]
    row_index: int
    platoon: Optional[str]


@dataclass
class FormResponseRecord:
    import_id: int
    row_index: int
    tank_id: Optional[str]
    timestamp: Optional[datetime]
    fields_json: str
