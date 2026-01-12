from typing import List, Dict, Any
from spearhead.domain.models import VehicleReport, BattalionData, ReadinessStatus
import logging

logger = logging.getLogger(__name__)

class RuleBasedAI:
    """
    Simulates a structured AI inference engine.
    Enforces fixed output format:
    {
        "severity_score": int (0-100),
        "recommended_action": str,
        "reasoning": str
    }
    """
    name = "ai_inference"

    def analyze(self, vehicle_id: str, reports: List[VehicleReport], data: BattalionData) -> None:
        # We only infer for the latest report of the vehicle
        if not reports:
            return
            
        latest = reports[-1]
        
        # 1. Calculate Severity
        severity = 0
        reasons = []
        
        # Status weight
        if latest.readiness == ReadinessStatus.UNAVAILABLE:
            severity += 80
            reasons.append("Vehicle is immobilized.")
        elif latest.readiness == ReadinessStatus.DEGRADED:
            severity += 40
            reasons.append("Vehicle capability degraded.")
            
        # Faults weight
        for fault in latest.fault_codes:
            severity += 15
            reasons.append(f"Active fault: {fault}")
            
        # Integrity weight
        if latest.integrity_flags:
            severity += 10
            reasons.append("Reporting integrity suspect.")
            
        # Logistics cap
        if latest.logistics_gap:
             severity += 5
             reasons.append(f"Logistics shortage: {latest.logistics_gap}")

        severity = min(severity, 100)
        
        # 2. Determine Action
        if severity >= 80:
            action = "IMMEDIATE_EVAC"
        elif severity >= 50:
            action = "MAINTENANCE_24H"
        elif severity >= 20:
            action = "MONITOR"
        else:
            action = "NO_ACTION"
            
        # 3. Construct Structured Output
        output = {
            "severity_score": severity,
            "recommended_action": action,
            "reasoning": "; ".join(reasons) if reasons else "All systems nominal."
        }
        
        latest.ai_inference = output
        logger.debug(f"AI Inference for {vehicle_id}: {output}")

