from pathlib import Path
import pytest
from spearhead.data.field_mapper import FieldMapper
from spearhead.data.repositories import BaseRepository

def test_platoon_inference_enforces_english_keys():
    """
    Architectural Rule: Platoon names must be normalized to English keys internally.
    Display layer handles Hebrew translation.
    """
    mapper = FieldMapper()
    
    # Simulate a file path with Hebrew name
    hebrew_path = Path("some/path/to/טופס כפיר 2024.xlsx")
    
    # MOCK the config if necessary, but we expect defaults to work.
    # We rely on defaults in config_fields.py
    
    inferred = mapper.infer_platoon(hebrew_path)
    
    assert inferred == "Kfir", f"Expected 'Kfir' (English key), got '{inferred}'. Internal keys must be English."

def test_scope_normalization_handles_hebrew_input():
    """
    Architectural Rule: Repository must accept Hebrew display names 
    and normalize them to English keys for DB filtering.
    """
    # Mock dataframe not needed if we test the static method directly
    # But _normalize_platoon is static in BaseRepository
    
    normalized = BaseRepository._normalize_platoon("כפיר")
    assert normalized == "Kfir"
    
    normalized_caps = BaseRepository._normalize_platoon("Kfir")
    assert normalized_caps == "Kfir"

def test_mapper_config_integrity():
    """
    Ensure config is loaded and has expected rules.
    """
    mapper = FieldMapper()
    # Check if 'Kfir' rule exists
    rules = [r for r in mapper.config.form.platoon_inference.file_names if r.get("platoon") == "Kfir"]
    assert len(rules) > 0, "Missing configuration rule for 'Kfir'"
    matches = [r.get("match") for r in rules]
    assert "כפיר" in matches or "kfir" in matches

