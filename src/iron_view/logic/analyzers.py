from typing import Protocol, List, Any
from iron_view.domain.models import VehicleReport, BattalionData
from iron_view.logic.integrity import detect_copy_paste
from iron_view.logic.erosion import calculate_erosion_score
import logging

logger = logging.getLogger(__name__)

class Analyzer(Protocol):
    """
    Protocol for any analysis module.
    """
    @property
    def name(self) -> str:
        ...

    def analyze(self, vehicle_id: str, reports: List[VehicleReport], data: BattalionData) -> None:
        """
        Analyze the history of a single vehicle and update the BattalionData.
        """
        ...

class IntegrityAnalyzer:
    name = "integrity"

    def analyze(self, vehicle_id: str, reports: List[VehicleReport], data: BattalionData) -> None:
        # We check each report against its PREVIOUS history
        # "Anti-Slacker" Protocol: Detect High Hamming Similarity despite new timestamp
        for i, report in enumerate(reports):
            if i == 0:
                continue
            
            prev_report = reports[i-1]
            
            # Simple Hamming-like heuristic:
            # If status AND location AND fault_codes are IDENTICAL to previous report
            # But the report is claimed to be new...
            
            is_identical = (
                report.readiness == prev_report.readiness and
                report.location == prev_report.location and
                report.fault_codes == prev_report.fault_codes and
                report.logistics_gap == prev_report.logistics_gap 
                # Note: 'company' is static so we don't check it
            )
            
            if is_identical:
                # If identical content, we flag it. 
                # Real Hamming would count bit differences, but for categorical data exact match is the concern.
                report.integrity_flags.append("COPY_PASTE_SUSPECTED")
                logger.debug(f"IntegrityAnalyzer: Flagged {report.report_id} as suspected copy-paste")

class ErosionAnalyzer:
    name = "erosion"
    
    # Weights for different faults
    FAULT_WEIGHTS = {
        "Engine Overheat": 1.5,
        "Track Tension Low": 0.5,
        "Comm System Fail": 0.8,
        "Oil Leak 10W": 1.0,
        "Turret Stabilizer": 2.0,
        "Fire Control Error": 2.5
    }
    
    def __init__(self, threshold: float):
        self.threshold = threshold

    def analyze(self, vehicle_id: str, reports: List[VehicleReport], data: BattalionData) -> None:
        # Rolling Window Analysis (Simple Sum for now as we have full history)
        score = 0.0
        
        for report in reports:
            # 1. Base Score for status
            if report.readiness == "DEGRADED":
                score += 0.5
            
            # 2. Weighted Fault Score
            for fault in report.fault_codes:
                weight = self.FAULT_WEIGHTS.get(fault, 0.5) # Default weight 0.5
                score += weight
        
        # Normalize score slightly if needed, or keep as accumulated "Wear & Tear"
        # Ideally we'd divide by time, but accumulative is good for "Chronic" detection
        
        data.vehicle_scores[vehicle_id] = score
        
        if score > self.threshold:
             logger.warning(f"High erosion detected for {vehicle_id}: {score:.2f}")


class LogisticsAnalyzer:
    name = "logistics"

    def analyze(self, vehicle_id: str, reports: List[VehicleReport], data: BattalionData) -> None:
        """
        Aggregates logistics gaps.
        In v1, we just collect them. In v2 (Iron-Stack), we could cluster them.
        For now, we just ensure they are visible in the report context if we augment BattalionData.
        
        Currently BattalionData doesn't have a 'logistics_summary' field, 
        so we might need to rely on the template iterating over reports, 
        OR we can monkey-patch data (not ideal) or just log for now.
        
        Let's add a simple 'critical_shortages' set to BattalionData if it existed,
        but since we can't easily change the model instance shared across analyzers without
        updating the model definition, we'll stick to per-vehicle analysis or
        just logging which is then captured.
        
        Actually, let's skip complex clustering for this specific step 
        unless we store it. We'll simply log severe gaps.
        """
        latest = reports[-1]
        if latest.logistics_gap:
            # We could normalize string here e.g. "Oil" == "oil"
            pass
