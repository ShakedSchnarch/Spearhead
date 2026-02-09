from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from spearhead.api import create_app
from spearhead.config import settings


BASE = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def reset_security():
    """
    Ensure security settings are restored after each test since settings is a module-level singleton.
    """
    original = {
        "api_token": settings.security.api_token,
        "require_queries": settings.security.require_auth_on_queries,
        "max_upload_mb": settings.security.max_upload_mb,
    }
    yield
    settings.security.api_token = original["api_token"]
    settings.security.require_auth_on_queries = original["require_queries"]
    settings.security.max_upload_mb = original["max_upload_mb"]


def test_import_requires_token_when_configured(tmp_path):
    settings.security.api_token = "secret-token"
    db_path = tmp_path / "spearhead.db"
    app = create_app(db_path=db_path)
    client = TestClient(app)

    loadout = BASE / "docs/archive/samples/דוחות פלוגת כפיר.xlsx"
    with open(loadout, "rb") as f:
        resp = client.post(
            "/imports/platoon-loadout",
            files={"file": (loadout.name, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
    assert resp.status_code == 401

    with open(loadout, "rb") as f:
        resp_ok = client.post(
            "/imports/platoon-loadout",
            files={"file": (loadout.name, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers={"Authorization": "Bearer secret-token"},
        )
    assert resp_ok.status_code == 200
    assert resp_ok.json()["inserted"] > 0


def test_queries_require_token_when_enabled(tmp_path):
    settings.security.api_token = "secret-token"
    settings.security.require_auth_on_queries = True
    db_path = tmp_path / "spearhead.db"
    app = create_app(db_path=db_path)
    client = TestClient(app)

    resp = client.get("/queries/tabular/totals", params={"section": "zivud"})
    assert resp.status_code == 401

    resp_ok = client.get(
        "/queries/tabular/totals",
        params={"section": "zivud"},
        headers={"Authorization": "Bearer secret-token"},
    )
    assert resp_ok.status_code == 200
    assert isinstance(resp_ok.json(), list)


def test_upload_rejected_when_too_large(tmp_path):
    settings.security.max_upload_mb = 0
    db_path = tmp_path / "spearhead.db"
    app = create_app(db_path=db_path)
    client = TestClient(app)

    loadout = BASE / "docs/archive/samples/דוחות פלוגת כפיר.xlsx"
    with open(loadout, "rb") as f:
        resp = client.post(
            "/imports/platoon-loadout",
            files={"file": (loadout.name, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
    assert resp.status_code == 413
