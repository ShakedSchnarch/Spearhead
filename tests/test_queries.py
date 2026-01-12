from pathlib import Path
from datetime import datetime, UTC

from spearhead.data.import_service import ImportService
from spearhead.services import QueryService


BASE = Path(__file__).resolve().parents[1]


def bootstrap_db(tmp_path):
    db_path = tmp_path / "spearhead.db"
    svc = ImportService(db_path=db_path)
    svc.import_platoon_loadout(BASE / "docs/Files/דוחות פלוגת כפיר.xlsx")
    svc.import_form_responses(BASE / "docs/Files/טופס דוחות סמפ כפיר. (תגובות).xlsx")
    return db_path


def test_tabular_totals_and_gaps(tmp_path):
    db_path = bootstrap_db(tmp_path)
    qs = QueryService(db=ImportService(db_path).db)

    totals = qs.tabular_totals("zivud")
    assert totals, "Expected totals for zivud section"
    assert any(t["total"] > 0 for t in totals)

    gaps = qs.tabular_gaps("zivud")
    # gaps may be empty if no explicit gap tokens, but call should not fail
    assert isinstance(gaps, list)


def test_form_status_counts(tmp_path):
    db_path = bootstrap_db(tmp_path)
    qs = QueryService(db=ImportService(db_path).db)

    status = qs.form_status_counts()
    assert "gaps" in status and "ok" in status
    assert isinstance(status["gaps"], list)
    assert isinstance(status["ok"], list)


def test_variance_and_delta(tmp_path):
    db_path = bootstrap_db(tmp_path)
    qs = QueryService(db=ImportService(db_path).db)

    variance = qs.tabular_variance_vs_summary("zivud")
    assert isinstance(variance, list)
    if variance:
        assert "direction" in variance[0]

    delta = qs.tabular_delta("zivud")
    # With a single import, delta will be empty but should not error
    assert isinstance(delta, list)
    if delta:
        assert "direction" in delta[0]


def test_filtered_queries_and_trends(tmp_path):
    db_path = bootstrap_db(tmp_path)
    qs = QueryService(db=ImportService(db_path).db)

    platoon_name = "דוחות פלוגת כפיר (1)"
    current_week = qs._week_label_from_datetime(datetime.now(UTC))

    totals_filtered = qs.tabular_totals("zivud", platoon=platoon_name, week=current_week)
    assert isinstance(totals_filtered, list)

    gaps_filtered = qs.tabular_gaps("zivud", platoon=platoon_name, week=current_week)
    assert isinstance(gaps_filtered, list)

    trends = qs.tabular_trends("zivud", top_n=3, platoon=platoon_name, window_weeks=12)
    assert isinstance(trends, list)
    if trends:
        assert "points" in trends[0]
