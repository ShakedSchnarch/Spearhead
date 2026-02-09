import sys
from unittest.mock import MagicMock
import pandas as pd

# Add src to path
sys.path.append("src")

from spearhead.logic.scoring import ScoringEngine, TankScore
from spearhead.services.intelligence import IntelligenceService
from spearhead.data.repositories import FormRepository

def test_scoring_logic():
    print("--- Testing Scoring Engine ---")
    engine = ScoringEngine()

    # 1. Perfect Tank
    tank = engine.calculate_tank_score(
        tank_id="101",
        zivud_gaps=[],
        ammo_status={"pgoz": 1.0},
        completeness_checks={"has_form": True},
        issues=[]
    )
    print(f"Perfect Tank Score: {tank.score} (Expected ~100) -> Grade: {tank.grade}")
    assert tank.score >= 99, f"Expected 100, got {tank.score}"

    # 2. Critical Veto
    tank_veto = engine.calculate_tank_score(
        tank_id="102",
        zivud_gaps=[],
        ammo_status={},
        completeness_checks={},
        issues=["תקלת ירי חמורה"] # Keywords: תקלת ירי
    )
    print(f"Veto Tank Score: {tank_veto.score} (Expected 0) -> Criticals: {tank_veto.critical_gaps}")
    assert tank_veto.score == 0.0, f"Expected 0, got {tank_veto.score}"
    assert "תקלת ירי חמורה" in tank_veto.critical_gaps

    # 3. Zivud Deductions
    # Missing 4 items * 5 points = -20 points from Zivud (which is 40% of total)
    # So Zivud Subscore = 80. Contribution = 80 * 0.4 = 32.
    # Ammo (30%) = 100 * 0.3 = 30.
    # Completeness (30%) = 100 * 0.3 = 30.
    # Total = 32+30+30 = 92
    tank_gaps = engine.calculate_tank_score(
        tank_id="103",
        zivud_gaps=["Item1", "Item2", "Item3", "Item4"],
        ammo_status={"a": 1.0},
        completeness_checks={"ok": True},
        issues=[]
    )
    print(f"Gaps Tank Score: {tank_gaps.score} (Expected ~92.0)")
    assert 90 <= tank_gaps.score <= 94, f"Expected ~92, got {tank_gaps.score}"

    print(">>> Scoring Logic PASS")

def test_service_integration():
    print("\n--- Testing Service Integration ---")
    mock_repo = MagicMock(spec=FormRepository)
    # Mock DF return
    mock_repo.get_forms.return_value = pd.DataFrame([{
        "tank_id": "999",
        "fields_json": '{"some_key": "some_value"}',
        "platoon": "TestPlatoon"
    }])
    mock_repo.get_unique_values.return_value = ["TestPlatoon"]
    mock_repo.get_latest_week.return_value = "2025-W01"

    engine = ScoringEngine()
    service = IntelligenceService(repository=mock_repo, scoring_engine=engine)

    # Test Platoon Intelligence
    intel = service.get_platoon_intelligence("TestPlatoon")
    print(f"Platoon Readiness: {intel.readiness_score}")
    print(f"Tanks Scored: {len(intel.tank_scores)}")
    
    # Test Battalion Intelligence
    bat_intel = service.get_battalion_intelligence()
    print(f"Battalion Readiness: {bat_intel.overall_readiness}")
    
    print(">>> Service Integration PASS")

if __name__ == "__main__":
    test_scoring_logic()
    test_service_integration()
