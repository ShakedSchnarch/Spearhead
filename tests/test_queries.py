from pathlib import Path

from iron_view.data.import_service import ImportService
from iron_view.services import QueryService


BASE = Path(__file__).resolve().parents[1]


def bootstrap_db(tmp_path):
    db_path = tmp_path / "ironview.db"
    svc = ImportService(db_path=db_path)
    svc.import_platoon_loadout(BASE / "docs/Files/דוחות פלוגת כפיר (1).xlsx")
    svc.import_form_responses(BASE / "docs/Files/טופס דוחות סמפ כפיר. (תגובות) (1).xlsx")
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
