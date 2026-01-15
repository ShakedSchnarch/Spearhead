from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

@dataclass
class TankScore:
    tank_id: str
    score: float  # 0-100
    grade: str    # "A", "B", "C", "F"
    critical_gaps: List[str]  # List of items causing veto or major deduction
    breakdown: Dict[str, float]  # { "zivud": 40, "ammo": 30, "completeness": 30 }
    top_missing_items: List[str] # Specific items for the "Priority List"
    family_breakdown: Optional[Dict[str, float]] = None  # alias for breakdown with families (zivud/ammo/comms/completeness)
    deltas: Optional[Dict[str, Optional[float]]] = None  # week-over-week change per family/overall
    gap_counts: Optional[Dict[str, int]] = None  # gaps per family for this tank
    trend: Optional[List["TrendPoint"] | str] = None  # historical series; string kept for backward compat

@dataclass
class PlatoonIntelligence:
    platoon: str
    week: str
    readiness_score: float # Aggregate 0-100
    tank_scores: List[TankScore]
    # Aggregated Insights
    critical_tanks_count: int
    top_gaps_battalion_level: List[str] = field(default_factory=list)
    breakdown: Optional[Dict[str, float]] = None
    deltas: Optional[Dict[str, Optional[float]]] = None
    coverage: Optional[Dict[str, int]] = None
    top_gaps_platoon: Optional[List[Dict[str, Any]]] = None

@dataclass
class BattalionIntelligence:
    week: str
    overall_readiness: float
    platoons: Dict[str, PlatoonIntelligence]
    comparison: Dict[str, float] # { "Kfir": 88.5, "Sufa": 92.0 }
    deltas: Optional[Dict[str, Optional[float]]] = None
    top_gaps_battalion: Optional[List[Dict[str, Any]]] = None

@dataclass
class GapReport:
    """Legacy/Existing DTO for raw gap reporting, kept for compatibility if needed."""
    platoon: str
    tank_id: str
    week: str
    gaps: List[str]

@dataclass
class FormResponseRow:
    """Intermediate representation of a raw form row for processing."""
    source_file: Optional[str]
    platoon: str
    row_index: int
    tank_id: Optional[str]
    timestamp: Optional[str]
    week_label: Optional[str]
    fields: Dict[str, Any]

@dataclass
class TabularRecord:
    """Flattened record from auxiliary Excel sheets (zivud, ammo, summaries)."""
    source_file: str
    section: str
    item: str
    column: str
    value: Any
    row_index: int
    platoon: Optional[str] = None

@dataclass
class TrendPoint:
    """Represents a single point in a trend line."""
    week: str
    score: float
    gaps: int = 0
    label: Optional[str] = None
