from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

from spearhead.api import create_app
from openpyxl import Workbook


BASE = Path(__file__).resolve().parents[1]


def test_api_imports_and_queries(tmp_path):
    db_path = tmp_path / "spearhead.db"
    app = create_app(db_path=db_path)
    client = TestClient(app)

    # Import platoon loadout
    loadout = BASE / "docs/Files/דוחות פלוגת כפיר.xlsx"
    with open(loadout, "rb") as f:
        resp = client.post(
            "/imports/platoon-loadout",
            files={"file": (loadout.name, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
    assert resp.status_code == 200
    assert resp.json()["inserted"] > 0

    # Import form responses
    form_file = BASE / "docs/Files/טופס דוחות סמפ כפיר. (תגובות).xlsx"
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

    # Delta and variance endpoints should respond (even if empty)
    resp = client.get("/queries/tabular/delta", params={"section": "zivud"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    resp = client.get("/queries/tabular/variance", params={"section": "zivud"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    resp = client.get("/queries/trends", params={"section": "zivud", "top_n": 3, "weeks": 12})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    resp = client.get("/insights", params={"section": "zivud"})
    assert resp.status_code == 200
    body = resp.json()
    assert "content" in body and "source" in body

    # Intelligence V2 fields
    platoon_intel = client.get("/intelligence/platoon/כפיר").json()
    assert "breakdown" in platoon_intel
    assert "coverage" in platoon_intel
    assert isinstance(platoon_intel.get("tank_scores"), list)

    battalion_intel = client.get("/intelligence/battalion").json()
    assert "top_gaps_battalion" in battalion_intel
    assert "comparison" in battalion_intel


def test_missing_required_headers_returns_422(tmp_path):
    """
    Uploading a form file without tank_id should raise a 422 with a clear message.
    """
    db_path = tmp_path / "spearhead.db"
    app = create_app(db_path=db_path)
    client = TestClient(app)

    wb = Workbook()
    ws = wb.active
    ws.append(["חותמת זמן", "דוח זיווד [חבל פריסה]"])
    ws.append([datetime.now(), "חוסר"])
    path = tmp_path / "missing_tank.xlsx"
    wb.save(path)

    with open(path, "rb") as f:
        resp = client.post(
            "/imports/form-responses",
            files={"file": (path.name, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )

    assert resp.status_code == 422
    body = resp.json()
    assert "Missing required columns" in body.get("detail", "")


def test_form_summary_modes(tmp_path):
    db_path = tmp_path / "spearhead.db"
    app = create_app(db_path=db_path)
    client = TestClient(app)

    # Seed form data
    form_file = BASE / "docs/Files/טופס דוחות סמפ כפיר. (תגובות).xlsx"
    with open(form_file, "rb") as f:
        resp = client.post(
            "/imports/form-responses",
            files={"file": (form_file.name, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
    assert resp.status_code == 200

    resp = client.get("/queries/forms/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "battalion"
    assert "platoons" in data and data["platoons"]

    resp = client.get("/queries/forms/summary", params={"mode": "platoon", "platoon": "כפיר"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "platoon"
    assert data["platoon"] == "כפיר"
