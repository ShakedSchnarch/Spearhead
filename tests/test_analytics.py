from pathlib import Path

from iron_view.data.import_service import ImportService
from iron_view.services.analytics import FormAnalytics
from iron_view.services.exporter import ExcelExporter

BASE = Path(__file__).resolve().parents[1]
FORM_FILE = BASE / "docs/Files/טופס דוחות סמפ כפיר. (תגובות).xlsx"


def bootstrap_forms(tmp_path):
    db_path = tmp_path / "ironview.db"
    svc = ImportService(db_path=db_path)
    svc.import_form_responses(FORM_FILE)
    return svc


def test_form_analytics_counts(tmp_path):
    svc = bootstrap_forms(tmp_path)
    analytics = FormAnalytics(svc.db)

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


def test_exports(tmp_path):
    svc = bootstrap_forms(tmp_path)
    analytics = FormAnalytics(svc.db)
    exporter = ExcelExporter(analytics, output_dir=tmp_path)

    week = analytics.latest_week()
    paths = exporter.export_all_for_week(week=week)

    assert "platoon:כפיר" in paths
    assert paths["battalion"].exists()
    assert paths["platoon:כפיר"].exists()
