from pathlib import Path

from spearhead.ai.insight_service import InsightService
from spearhead.ai.client import BaseAIClient, AIResult, SimulatedAIClient
from spearhead.data.import_service import ImportService
from spearhead.services import QueryService


BASE = Path(__file__).resolve().parents[1]


class FailingAIClient(BaseAIClient):
    def generate(self, prompt: str, context: str) -> AIResult:
        raise RuntimeError("fail")


def bootstrap_db(tmp_path):
    db_path = tmp_path / "spearhead.db"
    svc = ImportService(db_path=db_path)
    svc.import_platoon_loadout(BASE / "docs/archive/samples/דוחות פלוגת כפיר.xlsx")
    svc.import_battalion_summary(BASE / "docs/archive/samples/מסמך דוחות גדודי.xlsx")
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
