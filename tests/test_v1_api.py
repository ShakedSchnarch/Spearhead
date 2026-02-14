from pathlib import Path
import json
import sqlite3

from fastapi.testclient import TestClient

from spearhead.api.main import create_app
from spearhead.config import settings
from spearhead.data.storage import Database
from spearhead.v1 import ResponseQueryServiceV2, ResponseStore


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


def _company_assets_event(
    company: str = "כפיר",
    *,
    ts: str = "2026-02-08T10:00:00Z",
):
    return {
        "schema_version": "v2",
        "source_id": "manual-company-assets",
        "payload": {
            "פלוגה": company,
            "חותמת זמן": ts,
            'ח"ח פלוגתי [מד מומנט]': "חוסר",
            "2640 אקסטרה פלוגתי": "יש",
            'דוח צלם- נוספים [מאג 1]': "תקול",
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

    weeks_meta = client.get("/v1/metadata/weeks")
    assert weeks_meta.status_code == 200
    weeks_body = weeks_meta.json()
    assert weeks_body["weeks"]
    assert weeks_body["week_options"]
    first_option = weeks_body["week_options"][0]
    assert first_option["value"] == weeks_body["weeks"][0]
    assert "label" in first_option
    assert "start_date" in first_option
    assert "end_date" in first_option
    assert weeks_body["week_starts_on"] == "sunday"
    assert weeks_body["timezone"] == "Asia/Jerusalem"

    trends = client.get("/v1/queries/trends", params={"metric": "reports", "window_weeks": 4})
    assert trends.status_code == 200
    assert trends.json()["rows"]

    search = client.get("/v1/queries/search", params={"q": "חבל"})
    assert search.status_code == 200
    assert search.json()["rows"]


def test_v1_duplicate_reprocesses_when_normalized_missing(tmp_path):
    db_path = tmp_path / "v1_duplicate_reprocess.db"
    settings.storage.backend = "sqlite"
    settings.security.api_token = None
    settings.security.basic_user = None
    settings.security.basic_pass = None

    app = create_app(db_path=db_path)
    client = TestClient(app)

    first = client.post("/v1/ingestion/forms/events", json=_sample_event())
    assert first.status_code == 200
    assert first.json()["created"] is True
    event_id = first.json()["event_id"]

    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM normalized_responses_v2 WHERE event_id = ?", (event_id,))
        conn.execute(
            "UPDATE raw_form_events_v2 SET status = ?, error_detail = ? WHERE event_id = ?",
            ("invalid", "legacy-parse-error", event_id),
        )
        conn.commit()

    duplicate = client.post("/v1/ingestion/forms/events", json=_sample_event())
    assert duplicate.status_code == 200
    duplicate_body = duplicate.json()
    assert duplicate_body["created"] is False
    assert duplicate_body["event_id"] == event_id
    assert duplicate_body["platoon_key"] == "Kfir"
    assert duplicate_body["week_id"]

    overview = client.get("/v1/metrics/overview")
    assert overview.status_code == 200
    assert overview.json()["reports"] == 1


def test_v1_company_assets_duplicate_reprocesses_when_normalized_missing(tmp_path):
    db_path = tmp_path / "v1_company_assets_duplicate_reprocess.db"
    settings.storage.backend = "sqlite"
    settings.security.api_token = None
    settings.security.basic_user = None
    settings.security.basic_pass = None

    app = create_app(db_path=db_path)
    client = TestClient(app)

    payload = _company_assets_event(company="מחץ")
    first = client.post("/v1/ingestion/forms/company-assets", json=payload)
    assert first.status_code == 200
    assert first.json()["created"] is True
    event_id = first.json()["event_id"]

    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM normalized_company_assets_v2 WHERE event_id = ?", (event_id,))
        conn.execute(
            "UPDATE raw_form_events_v2 SET status = ?, error_detail = ? WHERE event_id = ?",
            ("invalid", "legacy-parse-error", event_id),
        )
        conn.commit()

    duplicate = client.post("/v1/ingestion/forms/company-assets", json=payload)
    assert duplicate.status_code == 200
    body = duplicate.json()
    assert body["created"] is False
    assert body["event_id"] == event_id
    assert body["company_key"] == "Mahatz"
    assert body["week_id"]

    assets = client.get("/v1/views/companies/Mahatz/assets", params={"week": body["week_id"]})
    assert assets.status_code == 200
    assert assets.json()["rows"]


def test_v1_command_views(tmp_path):
    db_path = tmp_path / "v1_views.db"
    settings.storage.backend = "sqlite"
    settings.security.api_token = None
    settings.security.basic_user = None
    settings.security.basic_pass = None
    settings.ai.enabled = False

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

    assets_resp = client.post("/v1/ingestion/forms/company-assets", json=_company_assets_event())
    assert assets_resp.status_code == 200
    assert assets_resp.json()["created"] is True

    battalion = client.get("/v1/views/battalion")
    assert battalion.status_code == 200
    battalion_body = battalion.json()
    assert battalion_body["rows"]
    assert {"Armament", "Logistics", "Communications"}.issubset(set(battalion_body["sections"]))
    assert {"Kfir", "Mahatz", "Sufa"}.issubset(set(battalion_body["companies"]))
    assert "trends" in battalion_body
    assert "readiness_by_company" in battalion_body["trends"]

    battalion_ai = client.get("/v1/views/battalion/ai-analysis")
    assert battalion_ai.status_code == 200
    battalion_ai_body = battalion_ai.json()
    assert battalion_ai_body["source"] == "deterministic"
    assert battalion_ai_body["structured"]["headline"]
    assert battalion_ai_body["structured"]["status"] in {"green", "yellow", "red"}
    assert len(battalion_ai_body["structured"]["key_findings"]) == 3
    assert len(battalion_ai_body["structured"]["immediate_risks"]) == 3
    assert len(battalion_ai_body["structured"]["actions_next_7_days"]) >= 3

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
    assert "critical_gaps_table" in company_tanks_body
    assert "ammo_averages" in company_tanks_body
    assert "trends" in company_tanks_body
    assert "tank_readiness" in company_tanks_body["trends"]
    assert "tank_series" in company_tanks_body["trends"]
    assert company_tanks_body["critical_gaps_table"]
    assert "tanks" in company_tanks_body["critical_gaps_table"][0]

    inventory = client.get("/v1/views/companies/Kfir/tanks/653/inventory")
    assert inventory.status_code == 200
    inventory_rows = inventory.json()["rows"]
    assert inventory_rows
    assert any(row["item"] == "חבל פריסה" for row in inventory_rows)
    assert any(row["standard_quantity"] is not None for row in inventory_rows)

    assets = client.get("/v1/views/companies/Kfir/assets")
    assert assets.status_code == 200
    assets_body = assets.json()
    assert assets_body["rows"]
    assert assets_body["summary"]["items"] >= 1
    assert any("standard_quantity" in row for row in assets_body["rows"])


def test_v1_alias_normalization_for_palsam_scope(tmp_path):
    db_path = tmp_path / "v1_palsam_aliases.db"
    settings.storage.backend = "sqlite"
    settings.security.api_token = None
    settings.security.basic_user = None
    settings.security.basic_pass = None

    app = create_app(db_path=db_path)
    client = TestClient(app)

    payload = _command_event("פלס״מ", "810", logistics="חוסר")
    ingest = client.post("/v1/ingestion/forms/events", json=payload)
    assert ingest.status_code == 200

    company = client.get("/v1/views/companies/palsam")
    assert company.status_code == 200
    body = company.json()
    assert body["company"] == "Palsam"
    assert len(body["sections"]) >= 3


def test_v1_battalion_ai_analysis_uses_remote_client_when_enabled(tmp_path, monkeypatch):
    db_path = tmp_path / "v1_ai_remote.db"
    settings.storage.backend = "sqlite"
    settings.security.api_token = None
    settings.security.basic_user = None
    settings.security.basic_pass = None

    class _FakeAIClient:
        def generate(self, prompt: str, context: str):
            class _Result:
                content = json.dumps(
                    {
                        "headline": "מצב גדודי דורש מיקוד",
                        "status": "yellow",
                        "executive_summary": "התמונה מצביעה על פערים קריטיים בלוגיסטיקה לצד שונות בין הפלוגות.",
                        "key_findings": [
                            {
                                "title": "כפיר עם העומס הגבוה",
                                "detail": "מספר פערים קריטיים גבוה ביחס לשאר הפלוגות.",
                                "severity": "high",
                                "company": "כפיר",
                            },
                            {
                                "title": "מחץ במגמת שיפור",
                                "detail": "שיפור יציב בכשירות השבועית.",
                                "severity": "medium",
                                "company": "מחץ",
                            },
                            {
                                "title": "סופה יציבה",
                                "detail": "רמת כשירות בינונית ללא שינוי חד.",
                                "severity": "low",
                                "company": "סופה",
                            },
                        ],
                        "immediate_risks": [
                            {
                                "risk": "פערים קריטיים פתוחים",
                                "reason": "מלאי חסר במספר פריטים קריטיים.",
                                "impact": "high",
                                "companies": ["כפיר"],
                            },
                            {
                                "risk": "ירידה נקודתית בכשירות",
                                "reason": "עלייה בפערי לוגיסטיקה.",
                                "impact": "medium",
                                "companies": ["כפיר", "סופה"],
                            },
                            {
                                "risk": "אי אחידות תהליכית",
                                "reason": "פער בין שיטות העבודה של הפלוגות.",
                                "impact": "medium",
                                "companies": ["גדוד"],
                            },
                        ],
                        "actions_next_7_days": [
                            {
                                "action": "סגירת פערים קריטיים לפי טנק.",
                                "priority": "p1",
                                "owner": "מפקדי פלוגות",
                                "expected_effect": "צמצום סיכון מיידי.",
                            },
                            {
                                "action": "בקרת כשירות יומית בחתך לוגיסטיקה.",
                                "priority": "p1",
                                "owner": "קצין לוגיסטיקה גדודי",
                                "expected_effect": "בלימת הידרדרות שבועית.",
                            },
                            {
                                "action": "יישור קו תהליכי בין הפלוגות.",
                                "priority": "p2",
                                "owner": "אג\"ם גדודי",
                                "expected_effect": "שיפור אחידות ביצוע.",
                            },
                        ],
                        "watch_next_week": [
                            "פערים קריטיים לפי פלוגה.",
                            "כשירות ממוצעת לפי פלוגה.",
                        ],
                        "data_quality": {
                            "coverage_note": "כיסוי דיווחים מספק לשבוע הנוכחי.",
                            "limitations": "ייתכנו פערים שלא דווחו.",
                        },
                    },
                    ensure_ascii=False,
                )
                source = "remote"

            return _Result()

    monkeypatch.setattr("spearhead.v1.service.build_ai_client", lambda _settings: _FakeAIClient())

    prev_enabled = settings.ai.enabled
    prev_provider = settings.ai.provider
    prev_base_url = settings.ai.base_url
    settings.ai.enabled = True
    settings.ai.provider = "http"
    settings.ai.base_url = "https://example.invalid/v1/chat/completions"

    try:
        app = create_app(db_path=db_path)
        client = TestClient(app)

        ingest = client.post(
            "/v1/ingestion/forms/events",
            json=_command_event("כפיר", "653", logistics="חוסר", communications="תקין"),
        )
        assert ingest.status_code == 200

        analysis = client.get("/v1/views/battalion/ai-analysis")
        assert analysis.status_code == 200
        body = analysis.json()
        assert body["source"] == "remote"
        assert body["structured"]["headline"] == "מצב גדודי דורש מיקוד"
        assert body["structured"]["status"] == "yellow"
        assert len(body["structured"]["key_findings"]) == 3
    finally:
        settings.ai.enabled = prev_enabled
        settings.ai.provider = prev_provider
        settings.ai.base_url = prev_base_url


def test_v1_ai_context_redacts_category_codes(tmp_path):
    db_path = tmp_path / "v1_ai_sanitize.db"
    store = ResponseStore(Database(db_path))
    svc = ResponseQueryServiceV2(store=store)

    payload = {
        "item": "מחסנית צ׳12345",
        "notes": ["בדיקת צ'9876", "ללא קוד"],
        "nested": {"code": "פריט צ׳ 654321"},
    }
    sanitized = svc._sanitize_ai_context(payload)
    rendered = json.dumps(sanitized, ensure_ascii=False)

    assert "12345" not in rendered
    assert "9876" not in rendered
    assert "654321" not in rendered
    assert rendered.count("[REDACTED]") == 3


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
