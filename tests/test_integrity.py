import pytest
from datetime import datetime, timedelta
from spearhead.logic.analyzers import IntegrityAnalyzer
from spearhead.domain.models import VehicleReport, BattalionData, ReadinessStatus

def create_report(vid, time_offset_minutes, status, location, faults, logistics, company="C1"):
    return VehicleReport(
        report_id=f"{vid}-{time_offset_minutes}",
        vehicle_id=vid,
        company=company,
        timestamp=datetime.now() + timedelta(minutes=time_offset_minutes),
        readiness=status,
        location=location,
        fault_codes=faults,
        logistics_gap=logistics
    )

def test_integrity_flags_copy_paste():
    analyzer = IntegrityAnalyzer()
    data = BattalionData()
    
    # 1. First report (Baseline)
    r1 = create_report("V1", 0, ReadinessStatus.OPERATIONAL, "Zone A", [], None)
    
    # 2. Identical report (Should flag)
    r2 = create_report("V1", 60, ReadinessStatus.OPERATIONAL, "Zone A", [], None)
    
    # 3. Different report (Should NOT flag)
    r3 = create_report("V1", 120, ReadinessStatus.DEGRADED, "Zone B", ["Engine Overheat"], None)

    reports = [r1, r2, r3]
    analyzer.analyze("V1", reports, data)
    
    assert not r1.integrity_flags
    assert "COPY_PASTE_SUSPECTED" in r2.integrity_flags
    assert not r3.integrity_flags

def test_integrity_ignores_first_report():
    analyzer = IntegrityAnalyzer()
    data = BattalionData()
    r1 = create_report("V1", 0, ReadinessStatus.OPERATIONAL, "Zone A", [], None)
    analyzer.analyze("V1", [r1], data)
    assert not r1.integrity_flags

def test_integrity_sensitive_to_location_change():
    analyzer = IntegrityAnalyzer()
    data = BattalionData()
    
    r1 = create_report("V1", 0, ReadinessStatus.OPERATIONAL, "Zone A", [], None)
    r2 = create_report("V1", 60, ReadinessStatus.OPERATIONAL, "Zone B", [], None) # Loc changed
    
    analyzer.analyze("V1", [r1, r2], data)
    assert not r2.integrity_flags # Should be clean because location changed
