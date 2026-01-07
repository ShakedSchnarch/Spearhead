import pytest
from datetime import datetime
from iron_view.logic.analyzers import ErosionAnalyzer
from iron_view.domain.models import VehicleReport, BattalionData, ReadinessStatus

def create_faulty_report(vid, status, faults):
    return VehicleReport(
        report_id=f"{vid}-x",
        vehicle_id=vid,
        company="C1",
        timestamp=datetime.now(),
        readiness=status,
        fault_codes=faults
    )

def test_erosion_score_calculation():
    analyzer = ErosionAnalyzer(threshold=0.5)
    data = BattalionData()
    
    # 1. Report with "Engine Overheat" (Weight 1.5)
    r1 = create_faulty_report("V1", ReadinessStatus.OPERATIONAL, ["Engine Overheat"])
    
    # 2. Report with "Track Tension Low" (Weight 0.5)
    r2 = create_faulty_report("V1", ReadinessStatus.OPERATIONAL, ["Track Tension Low"])
    
    analyzer.analyze("V1", [r1, r2], data)
    
    # Expected: 1.5 + 0.5 = 2.0
    assert data.vehicle_scores["V1"] == 2.0

def test_erosion_score_base_degraded():
    analyzer = ErosionAnalyzer(threshold=0.5)
    data = BattalionData()
    
    # Report is DEGRADED (Base 0.5) but no specific faults
    r1 = create_faulty_report("V1", ReadinessStatus.DEGRADED, [])
    
    analyzer.analyze("V1", [r1], data)
    
    assert data.vehicle_scores["V1"] == 0.5

def test_erosion_alert_logging(caplog):
    # Threshold is 1.0
    analyzer = ErosionAnalyzer(threshold=1.0)
    data = BattalionData()
    
    # Score 1.5 triggers alert
    r1 = create_faulty_report("V1", ReadinessStatus.OPERATIONAL, ["Engine Overheat"])
    
    analyzer.analyze("V1", [r1], data)
    
    assert "High erosion detected for V1" in caplog.text
