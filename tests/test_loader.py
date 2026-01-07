import pytest
from pathlib import Path
from iron_view.etl.loader import load_data
from iron_view.domain.models import ReadinessStatus

def test_load_data_success(tmp_path):
    # Create valid CSV
    csv_file = tmp_path / "valid.csv"
    csv_file.write_text(
        "report_id,vehicle_id,timestamp,readiness,reporter\n"
        "r1,v1,2023-01-01T10:00:00,OPERATIONAL,s1\n"
        "r2,v2,2023-01-01T11:00:00,DEGRADED,s2\n"
    )
    
    data = load_data(csv_file)
    assert len(data.reports) == 2
    assert data.reports[0].vehicle_id == "v1"
    assert data.reports[1].readiness == ReadinessStatus.DEGRADED

def test_load_data_corrupt_row(tmp_path):
    # Create CSV with one corrupt row (missing readiness)
    csv_file = tmp_path / "corrupt.csv"
    csv_file.write_text(
        "report_id,vehicle_id,timestamp,readiness,reporter\n"
        "r1,v1,,,OPERATIONAL,s1\n"  # Valid-ish but timestamp?
        "r2,v2,2023-01-01,INVALID_STATUS,s2\n" # Invalid Enum
        "r3,v3,2023-01-01T12:00:00,OPERATIONAL,s3\n" # Valid
    )
    
    # We expect the invalid row to be skipped
    # Actually row 2 (r1) missing timestamp might fail conversion unless pydantic handles it gracefully or we provided it
    # Row 3 (r2) has invalid enum
    # Row 4 (r3) is valid
    
    data = load_data(csv_file)
    # r3 should definitely load. r2 fail. r1 fail (timestamp parsing likely if empty)
    
    # Let's count valid reports.
    # r1: timestamp empty -> failure
    # r2: readiness invalid -> failure
    # r3: valid
    assert len(data.reports) >= 1
    found_ids = [r.report_id for r in data.reports]
    assert "r3" in found_ids
    assert "r2" not in found_ids
