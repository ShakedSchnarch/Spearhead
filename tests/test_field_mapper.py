import pytest
from pathlib import Path
from spearhead.data.field_mapper import FieldMapper

@pytest.fixture
def mapper():
    return FieldMapper()

@pytest.mark.parametrize("filename,expected_platoon", [
    ("Kfir.xlsx", "Kfir"),
    ("Mahatz_Export.csv", "Mahatz"),
    ("Sufa (תגובות).xlsx", "Sufa"),
    ("Kfir (תגובות).xlsx", "Kfir"),
    ("Spearhead_Export_Platoon_Mahatz_Week_10.xlsx", "Mahatz"),
    ("Unknown_Platoon.xlsx", None),
    ("Lahav_Export.csv", None), # "Lahav" is no longer a valid unit in our config
])
def test_infer_platoon_filenames(mapper, filename, expected_platoon):
    """
    Test that infer_platoon correctly identifies the platoon from the filename,
    ignoring noise like '(תגובות)' or 'Export'.
    """
    file_path = Path(f"/tmp/{filename}")
    assert mapper.infer_platoon(file_path) == expected_platoon


def test_infer_platoon_by_id(mapper):
    """
    Test that infer_platoon uses source_id mapping if provided,
    overriding (or independent of) filename.
    """
    # Known ID for Mahatz
    mahatz_id = "1kkdR41tCHJQQDCGMLzch-YCcxMiM1uSp-5MrEl9AAVY"
    # Generic filename that wouldn't parse on its own
    path = Path("/tmp/forms_response_0.xlsx")
    
    assert mapper.infer_platoon(path, source_id=mahatz_id) == "Mahatz"
    
    # Check that unknown ID falls back to filename
    assert mapper.infer_platoon(Path("/tmp/Kfir.xlsx"), source_id="unknown_id") == "Kfir"
