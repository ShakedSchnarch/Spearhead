from pathlib import Path
from spearhead.services.exporter import ExcelExporter
from spearhead.services.intelligence import IntelligenceService
from spearhead.logic.scoring import ScoringEngine

def test_form_analytics_counts(analytics):
    week = analytics.latest_week()
    assert week, "Expected week label derived from timestamps"

    summary_latest = analytics.summarize(week=week)
    platoon_latest = summary_latest["platoons"].get("כפיר")
    assert platoon_latest, "Platoon 'כפיר' should be detected from file name"
    assert platoon_latest.tank_count >= 1

    summary_all = analytics.summarize()
    platoon_summary = summary_all["platoons"]["כפיר"]
    assert platoon_summary.tank_count == 11

    ammo = platoon_summary.ammo
    assert "חלול" in ammo
    assert ammo["חלול"]["total"] == 93.0
    assert round(ammo["חלול"]["avg_per_tank"], 3) == round(93.0 / 11, 3)

    assert platoon_summary.zivud_gaps, "Should detect at least one zivud gap"
    means = platoon_summary.means
    assert means, "Expected means stats"
    assert "פתיל 5" in means
    assert means["פתיל 5"]["count"] == 2
    assert round(means["פתיל 5"]["avg_per_tank"], 3) == round(2 / 11, 3)

    assert summary_all["battalion"]["tank_count"] == 11
    assert summary_all["battalion"]["ammo"]["חלול"]["total"] == 93.0
    assert summary_all["battalion"]["means"]["פתיל 5"]["count"] == 2


def test_exports(bootstrap_service, analytics, form_repo, tmp_path):
    # Setup - use fixtures passed in
    engine = ScoringEngine()
    intel = IntelligenceService(form_repo, engine)
    exporter = ExcelExporter(analytics, intel, output_dir=tmp_path)

    week = analytics.latest_week()
    paths = exporter.export_all_for_week(week=week)

    assert "platoon:כפיר" in paths
    assert paths["battalion"].exists()
    assert paths["platoon:כפיר"].exists()


def test_form_analytics_coverage_platoon_filter(analytics):
    # Test battalion wide (no filter)
    coverage_all = analytics.coverage()
    assert "כפיר" in coverage_all["platoons"]
    
    # Test filtered by Hebrew Display Name
    coverage_kfir = analytics.coverage(platoon="כפיר")
    assert "כפיר" in coverage_kfir["platoons"]
    assert len(coverage_kfir["platoons"]) == 1
    assert coverage_kfir["platoons"]["כפיר"]["forms"] >= 1
    
    # Test filtered by English Key (Architecture Compliance)
    # The system should handle English keys if they are passed in scope
    coverage_kfir_eng = analytics.coverage(platoon="Kfir")
    # Output key is typically normalized for display, so it might be "כפיר" in the dict
    assert "כפיר" in coverage_kfir_eng["platoons"]
    assert len(coverage_kfir_eng["platoons"]) == 1

    # Test filtered (other platoon)
    coverage_sufa = analytics.coverage(platoon="סופה")
    assert "כפיר" not in coverage_sufa["platoons"]
