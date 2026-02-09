from pathlib import Path

from fastapi.testclient import TestClient

from spearhead.api.main import create_app
from spearhead.config import settings


def _sample_event(platoon: str = "כפיר", tank: str = "צ'653", gap: str = "חוסר"):
    return {
        "schema_version": "v2",
        "source_id": "manual-test",
        "payload": {
            "צ טנק": tank,
            "חותמת זמן": "2026-02-08T10:00:00Z",
            "פלוגה": platoon,
            "דוח זיווד [חבל פריסה]": gap,
            "ברוסי מאג": "קיים",
        },
    }


def test_v1_ingestion_and_queries(tmp_path, monkeypatch):
    db_path = tmp_path / "v1_api.db"
    settings.security.api_token = None
    settings.security.basic_user = None
    settings.security.basic_pass = None

    app = create_app(db_path=db_path)
    client = TestClient(app)

    resp = client.post("/v1/ingestion/forms/events", json=_sample_event())
    assert resp.status_code == 200
    body = resp.json()
    assert body["created"] is True
    assert body["event_id"]

    # Idempotent duplicate
    duplicate = client.post("/v1/ingestion/forms/events", json=_sample_event())
    assert duplicate.status_code == 200
    assert duplicate.json()["created"] is False

    overview = client.get("/v1/metrics/overview")
    assert overview.status_code == 200
    overview_body = overview.json()
    assert overview_body["reports"] == 1
    assert overview_body["tanks"] == 1
    assert overview_body["total_gaps"] >= 1

    gaps = client.get("/v1/queries/gaps", params={"group_by": "item"})
    assert gaps.status_code == 200
    assert gaps.json()["rows"]

    tanks = client.get("/v1/metrics/tanks", params={"platoon": "Kfir"})
    assert tanks.status_code == 200
    assert len(tanks.json()["rows"]) == 1

    trends = client.get("/v1/queries/trends", params={"metric": "reports", "window_weeks": 4})
    assert trends.status_code == 200
    assert trends.json()["rows"]

    search = client.get("/v1/queries/search", params={"q": "חבל"})
    assert search.status_code == 200
    assert search.json()["rows"]


def test_deprecated_endpoints_return_410(tmp_path):
    db_path = tmp_path / "deprecated.db"
    settings.security.api_token = None
    app = create_app(db_path=db_path)
    client = TestClient(app)

    export_resp = client.get("/exports/battalion", params={"week": "2026-W06"})
    assert export_resp.status_code == 410
    assert export_resp.headers.get("X-API-Deprecated") == "true"

    import_resp = client.post(
        "/imports/battalion-summary",
        files={"file": ("dummy.xlsx", b"x", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert import_resp.status_code == 410
    assert import_resp.headers.get("X-API-Deprecated") == "true"
