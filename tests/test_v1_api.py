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


def _command_event(
    platoon: str,
    tank: str,
    *,
    ts: str = "2026-02-08T10:00:00Z",
    logistics: str = "קיים",
    armament: str = "קיים",
    communications: str = "קיים",
):
    return {
        "schema_version": "v2",
        "source_id": "manual-command-view",
        "payload": {
            "צ טנק": tank,
            "חותמת זמן": ts,
            "פלוגה": platoon,
            "דוח זיווד [חבל פריסה]": logistics,
            "ברוסי מאג": armament,
            "סטטוס ציוד קשר [פתיל 5]": communications,
        },
    }


def test_v1_ingestion_and_queries(tmp_path, monkeypatch):
    db_path = tmp_path / "v1_api.db"
    settings.storage.backend = "sqlite"
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


def test_v1_command_views(tmp_path):
    db_path = tmp_path / "v1_views.db"
    settings.storage.backend = "sqlite"
    settings.security.api_token = None
    settings.security.basic_user = None
    settings.security.basic_pass = None

    app = create_app(db_path=db_path)
    client = TestClient(app)

    ingest_payloads = [
        _command_event(
            "כפיר",
            "653",
            logistics="חוסר",
            armament="חוסר",
            communications="קיים",
        ),
        _command_event(
            "מחץ",
            "721",
            logistics="קיים",
            armament="קיים",
            communications="חוסר",
        ),
    ]
    for payload in ingest_payloads:
        resp = client.post("/v1/ingestion/forms/events", json=payload)
        assert resp.status_code == 200

    battalion = client.get("/v1/views/battalion")
    assert battalion.status_code == 200
    battalion_body = battalion.json()
    assert battalion_body["rows"]
    assert {"Armament", "Logistics", "Communications"}.issubset(set(battalion_body["sections"]))
    assert "Kfir" in battalion_body["companies"]
    assert "Mahatz" in battalion_body["companies"]

    company = client.get("/v1/views/companies/Kfir")
    assert company.status_code == 200
    company_body = company.json()
    assert company_body["company"] == "Kfir"
    assert len(company_body["sections"]) >= 3
    assert "readiness_score" in company_body
    logistics_section = next(row for row in company_body["sections"] if row["section"] == "Logistics")
    assert logistics_section["total_gaps"] >= 1
    assert "readiness_score" in logistics_section
    assert "critical_gaps" in logistics_section

    tanks = client.get("/v1/views/companies/Kfir/sections/Logistics/tanks")
    assert tanks.status_code == 200
    tank_rows = tanks.json()["rows"]
    assert tank_rows
    assert tank_rows[0]["tank_id"] == "653"
    assert "readiness_score" in tank_rows[0]
    assert "critical_gaps" in tank_rows[0]

    company_tanks = client.get("/v1/views/companies/Kfir/tanks")
    assert company_tanks.status_code == 200
    company_tanks_body = company_tanks.json()
    assert company_tanks_body["rows"]
    assert company_tanks_body["rows"][0]["tank_id"] == "653"
    assert "logistics_readiness" in company_tanks_body["rows"][0]
    assert "summary" in company_tanks_body


def test_deprecated_endpoints_return_410(tmp_path):
    db_path = tmp_path / "deprecated.db"
    settings.storage.backend = "sqlite"
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


def test_v1_queries_require_auth_when_enabled(tmp_path):
    db_path = tmp_path / "auth_required.db"
    settings.storage.backend = "sqlite"
    settings.security.api_token = None
    settings.security.basic_user = None
    settings.security.basic_pass = None
    settings.security.require_auth_on_queries = True

    try:
        app = create_app(db_path=db_path)
        client = TestClient(app)
        ingest = client.post("/v1/ingestion/forms/events", json=_sample_event())
        assert ingest.status_code == 200

        overview = client.get("/v1/metrics/overview")
        assert overview.status_code == 401
    finally:
        settings.security.require_auth_on_queries = False
