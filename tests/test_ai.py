from pathlib import Path

from iron_view.ai.insight_service import InsightService
from iron_view.ai.client import BaseAIClient, AIResult, SimulatedAIClient
from iron_view.data.import_service import ImportService
from iron_view.services import QueryService


BASE = Path(__file__).resolve().parents[1]


class FailingAIClient(BaseAIClient):
    def generate(self, prompt: str, context: str) -> AIResult:
        raise RuntimeError("fail")


def bootstrap_db(tmp_path):
    db_path = tmp_path / "ironview.db"
    svc = ImportService(db_path=db_path)
    svc.import_platoon_loadout(BASE / "docs/Files/דוחות פלוגת כפיר (1).xlsx")
    svc.import_battalion_summary(BASE / "docs/Files/מסמך דוחות גדודי (1).xlsx")
    return svc.db


def test_insight_fallback_and_cache(tmp_path):
    db = bootstrap_db(tmp_path)
    qs = QueryService(db=db)
    svc = InsightService(db=db, query_service=qs, ai_client=FailingAIClient())

    first = svc.generate(section="zivud", top_n=3)
    assert first["source"] == "fallback"
    assert first["cached"] is False

    second = svc.generate(section="zivud", top_n=3)
    assert second["cached"] is True
    assert "content" in second


def test_insight_simulated_client(tmp_path):
    db = bootstrap_db(tmp_path)
    qs = QueryService(db=db)
    svc = InsightService(db=db, query_service=qs, ai_client=SimulatedAIClient())
    result = svc.generate(section="zivud")
    assert "SIMULATED" in result["content"]
