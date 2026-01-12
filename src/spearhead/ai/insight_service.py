import hashlib
import json
from datetime import datetime, UTC
from typing import Optional

from spearhead.ai.client import AIResult, BaseAIClient
from spearhead.config import settings
from spearhead.data.storage import Database
from spearhead.services import QueryService


class InsightService:
    """
    Generates AI-backed insights over deterministic query outputs with caching and safe fallbacks.
    """

    def __init__(self, db: Database, query_service: QueryService, ai_client: BaseAIClient):
        self.db = db
        self.query_service = query_service
        self.ai_client = ai_client

    def generate(self, section: str = "zivud", platoon: Optional[str] = None, top_n: int = 5) -> dict:
        """
        Returns {"content": str, "source": str, "cached": bool}
        """
        context = self._build_context(section=section, platoon=platoon, top_n=top_n)
        prompt = self._prompt_template(section, platoon)
        cache_key = self._cache_key(prompt, context)
        cached = self._maybe_get_cached(cache_key)
        if cached:
            return cached

        try:
            result: AIResult = self.ai_client.generate(prompt=prompt, context=context)
        except Exception:
            # Safe deterministic fallback using rule-based summary
            fallback_content = self._fallback_summary(section=section, platoon=platoon, top_n=top_n)
            result = AIResult(content=fallback_content, source="fallback", cached=False)

        self.db.insert_ai_insight(cache_key=cache_key, prompt=prompt, response=result.content, metadata_json="{}")
        return {"content": result.content, "source": result.source, "cached": result.cached}

    def _maybe_get_cached(self, cache_key: str) -> Optional[dict]:
        ttl_minutes = settings.ai.cache_ttl_minutes
        row = self.db.get_ai_insight(cache_key)
        if not row:
            return None
        created_at = row.get("created_at")
        if created_at:
            try:
                ts = datetime.fromisoformat(created_at)
                age_min = (datetime.now(UTC) - ts).total_seconds() / 60
                if age_min > ttl_minutes:
                    return None
            except Exception:
                return None
        return {"content": row["response"], "source": "cache", "cached": True}

    def _build_context(self, section: str, platoon: Optional[str], top_n: int) -> str:
        totals = self.query_service.tabular_totals(section=section, top_n=top_n, platoon=platoon)
        gaps = self.query_service.tabular_gaps(section=section, top_n=top_n, platoon=platoon)
        delta = self.query_service.tabular_delta(section=section, top_n=top_n)
        variance = self.query_service.tabular_variance_vs_summary(section=section, top_n=top_n)
        trends = self.query_service.tabular_trends(section=section, top_n=top_n, platoon=platoon, window_weeks=8)

        payload = {
            "section": section,
            "platoon": platoon,
            "totals": totals,
            "gaps": gaps,
            "delta": delta,
            "variance": variance,
            "trends": trends,
        }
        return json.dumps(payload, ensure_ascii=False)[:6000]  # bound context size

    def _prompt_template(self, section: str, platoon: Optional[str]) -> str:
        focus = f" for platoon {platoon}" if platoon else ""
        return (
            f"You are an assistant for tactical readiness. Summarize key risks and priorities for {section}{focus}. "
            "Be concise (<=120 words). Highlight items with gaps, negative trends, or variances. "
            "Always include 1-3 bullet recommendations."
        )

    def _fallback_summary(self, section: str, platoon: Optional[str], top_n: int) -> str:
        gaps = self.query_service.tabular_gaps(section=section, top_n=top_n, platoon=platoon)
        delta = self.query_service.tabular_delta(section=section, top_n=top_n)
        variance = self.query_service.tabular_variance_vs_summary(section=section, top_n=top_n)

        def top_str(items, key):
            if not items:
                return "none"
            return ", ".join(f"{i['item']} ({i[key]:.1f})" for i in items[:3] if isinstance(i.get(key), (int, float)))

        return (
            f"[DETERMINISTIC SUMMARY] Section={section} "
            f"Gaps top: {top_str(gaps, 'gaps')}; "
            f"Delta top: {top_str(delta, 'delta')}; "
            f"Variance top: {top_str(variance, 'variance')}."
        )

    @staticmethod
    def _cache_key(prompt: str, context: str) -> str:
        return hashlib.sha256(f"{prompt}|{context}".encode("utf-8")).hexdigest()
