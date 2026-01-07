from pathlib import Path

from fastapi.testclient import TestClient

from iron_view.api import create_app


BASE = Path(__file__).resolve().parents[1]


def test_api_imports_and_queries(tmp_path):
    db_path = tmp_path / "ironview.db"
    app = create_app(db_path=db_path)
    client = TestClient(app)

    # Import platoon loadout
    loadout = BASE / "docs/Files/דוחות פלוגת כפיר (1).xlsx"
    with open(loadout, "rb") as f:
        resp = client.post(
            "/imports/platoon-loadout",
            files={"file": (loadout.name, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
    assert resp.status_code == 200
    assert resp.json()["inserted"] > 0

    # Import form responses
    form_file = BASE / "docs/Files/טופס דוחות סמפ כפיר. (תגובות) (1).xlsx"
    with open(form_file, "rb") as f:
        resp = client.post(
            "/imports/form-responses",
            files={"file": (form_file.name, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
    assert resp.status_code == 200
    assert resp.json()["inserted"] > 0

    # Query totals
    resp = client.get("/queries/tabular/totals", params={"section": "zivud", "top_n": 5})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    # Query form status
    resp = client.get("/queries/forms/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "gaps" in data and "ok" in data
