from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field, field_validator


class ReadinessStatus(str, Enum):
    OPERATIONAL = "OPERATIONAL"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    MAINTENANCE = "MAINTENANCE"

    @property
    def heb(self) -> str:
        """Hebrew translation for display."""
        return {
            "OPERATIONAL": "כשיר",
            "DEGRADED": "כשירות חלקית",
            "UNAVAILABLE": "מושבת",
            "MAINTENANCE": "בטיפול",
        }[self.value]


class VehicleReport(BaseModel):
    """
    Represents a single readiness report for a vehicle.
    """
    report_id: str = Field(..., description="Unique identifier for the report")
    vehicle_id: str = Field(..., description="Unique identifier for the vehicle")
    timestamp: datetime = Field(..., description="Time of the report")
    readiness: ReadinessStatus = Field(..., description="Current readiness status")
    location: Optional[str] = Field(None, description="Current location shorthand")
    company: Optional[str] = Field(None, description="Company/Platoon")
    fault_codes: List[str] = Field(default_factory=list, description="List of technical fault codes")
    logistics_gap: Optional[str] = Field(None, description="Critical supply shortages (e.g. 'Oil 10W')")
    integrity_flags: List[str] = Field(default_factory=list, description="Automated integrity checks")
    ai_inference: Optional[Dict[str, Any]] = Field(None, description="Structured AI output (Severity, Action)")
    
    # "reporter" field removed for Privacy First compliance. 
    # "notes" removed in favor of structured fault_codes/logistics_gap.

    @field_validator("vehicle_id", "report_id", "logistics_gap", "company")
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return v.strip()

    @field_validator("vehicle_id")
    @classmethod
    def check_vehicle_id_not_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("vehicle_id cannot be empty")
        return v


class BattalionData(BaseModel):
    """
    Aggregated data for the entire battalion.
    """
    reports: List[VehicleReport] = Field(default_factory=list)
    vehicle_scores: dict[str, float] = Field(default_factory=dict, description="Erosion status per vehicle")
    
    # Phase 5 Enrichment
    logistics_summary: Dict[str, int] = {} # Map item -> count
    system_alerts: List[str] = [] # List of system-wide alerts
