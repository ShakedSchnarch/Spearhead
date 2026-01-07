import pytest
from datetime import datetime, timedelta
from iron_view.domain.models import VehicleReport, ReadinessStatus
from iron_view.logic.integrity import detect_copy_paste
from iron_view.logic.erosion import calculate_erosion_score

@pytest.fixture
def sample_report():
    return VehicleReport(
        report_id="r1",
        vehicle_id="v1",
        timestamp=datetime.now(),
        readiness=ReadinessStatus.OPERATIONAL,
        location="Base A",
        notes="All good",
        reporter="Soldier X"
    )

def test_detect_copy_paste_true(sample_report):
    history = [sample_report]
    current = sample_report.model_copy(update={
        "report_id": "r2", 
        "timestamp": datetime.now() + timedelta(days=1)
    })
    
    # Verify copy-paste detected
    assert detect_copy_paste(current, history) is True

def test_detect_copy_paste_false(sample_report):
    history = [sample_report]
    current = sample_report.model_copy(update={
        "report_id": "r2", 
        "timestamp": datetime.now() + timedelta(days=1),
        "notes": "Something different"
    })
    
    assert detect_copy_paste(current, history) is False

def test_erosion_score_perfect():
    history = [
        VehicleReport(
            report_id=f"r{i}", vehicle_id="v1", timestamp=datetime.now(),
            readiness=ReadinessStatus.OPERATIONAL, reporter="me"
        ) for i in range(5)
    ]
    assert calculate_erosion_score(history) == 0.0

def test_erosion_score_bad():
    history = [
        VehicleReport(
            report_id=f"r{i}", vehicle_id="v1", timestamp=datetime.now(),
            readiness=ReadinessStatus.UNAVAILABLE, reporter="me"
        ) for i in range(5)
    ]
    assert calculate_erosion_score(history) == 1.0

def test_erosion_score_mixed():
    # 2 bad, 2 good -> 0.5
    history = [
        VehicleReport(report_id="1", vehicle_id="v", timestamp=datetime.now(), readiness=ReadinessStatus.OPERATIONAL, reporter="u"),
        VehicleReport(report_id="2", vehicle_id="v", timestamp=datetime.now(), readiness=ReadinessStatus.OPERATIONAL, reporter="u"),
        VehicleReport(report_id="3", vehicle_id="v", timestamp=datetime.now(), readiness=ReadinessStatus.UNAVAILABLE, reporter="u"),
        VehicleReport(report_id="4", vehicle_id="v", timestamp=datetime.now(), readiness=ReadinessStatus.MAINTENANCE, reporter="u"),
    ]
    assert calculate_erosion_score(history) == 0.5
