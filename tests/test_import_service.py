import sqlite3
from pathlib import Path

from iron_view.data.import_service import ImportService


BASE = Path(__file__).resolve().parents[1]


def test_import_service_idempotent(tmp_path):
    db_path = tmp_path / "ironview.db"
    svc = ImportService(db_path=db_path)

    # Use small test file (form responses) to validate idempotency
    form_path = BASE / "docs/Files/טופס דוחות סמפ כפיר. (תגובות) (1).xlsx"
    inserted = svc.import_form_responses(form_path)
    assert inserted > 0

    # Re-import same file should reuse import_id and not duplicate records
    inserted_again = svc.import_form_responses(form_path)
    assert inserted_again == 0  # idempotent: second pass is skipped

    # Ensure only one import entry
    with sqlite3.connect(db_path) as conn:
        count_imports = conn.execute("SELECT COUNT(*) FROM imports").fetchone()[0]
        count_responses = conn.execute("SELECT COUNT(*) FROM form_responses").fetchone()[0]
    assert count_imports == 1
    assert count_responses == inserted


def test_import_service_tabular(tmp_path):
    db_path = tmp_path / "ironview.db"
    svc = ImportService(db_path=db_path)

    loadout_path = BASE / "docs/Files/דוחות פלוגת כפיר (1).xlsx"
    inserted = svc.import_platoon_loadout(loadout_path)
    assert inserted > 0

    with sqlite3.connect(db_path) as conn:
        count_records = conn.execute("SELECT COUNT(*) FROM tabular_records").fetchone()[0]
    assert count_records == inserted
