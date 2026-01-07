import json
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any

from iron_view.config import settings
from iron_view.config_fields import field_config
from iron_view.data.field_mapper import FieldMapper
from iron_view.data.storage import Database


@dataclass
class PlatoonSummary:
    platoon: str
    week: Optional[str]
    tank_count: int
    zivud_gaps: Dict[str, int]
    ammo: Dict[str, Dict[str, Optional[float]]]
    means: Dict[str, Dict[str, Optional[float]]]
    issues: List[Dict[str, str]]


class FormAnalytics:
    """
    Aggregates normalized insights from stored form responses using config-driven header aliases.
    - Dynamic tank counts per platoon/week (derived from distinct צ טנק)
    - Zivud gaps (חוסר/בלאי) per item
    - Ammo totals + per-tank averages
    - Means/comm gaps and free-text issues (for downstream reporting)
    - Optional פערי צלמים if present in form fields
    """

    def __init__(self, db: Database):
        self.db = db
        self.mapper = FieldMapper()
        # Extend tokens for common "missing" phrasing
        gap_source = settings.status_tokens.gap_tokens + field_config.gap_tokens + ["אין"]
        ok_source = settings.status_tokens.ok_tokens + field_config.ok_tokens + ["יש", "תקין"]
        # Keep order but drop duplicates
        self.gap_tokens = tuple(dict.fromkeys(gap_source))
        self.ok_tokens = tuple(dict.fromkeys(ok_source))

    def latest_week(self) -> Optional[str]:
        with self.db._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT week_label FROM form_responses WHERE week_label IS NOT NULL ORDER BY week_label DESC LIMIT 1"
            )
            row = cur.fetchone()
        return row[0] if row else None

    def platoons(self, week: Optional[str] = None) -> List[str]:
        filters = []
        params: List[str] = []
        if week:
            filters.append("week_label = ?")
            params.append(week)
        query = "SELECT DISTINCT platoon FROM form_responses WHERE platoon IS NOT NULL"
        if filters:
            query += " AND " + " AND ".join(filters)
        with self.db._connect() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            rows = cur.fetchall()
        return [r[0] for r in rows]

    def summarize(
        self,
        week: Optional[str] = None,
        platoon_override: Optional[str] = None,
        prefer_latest: bool = False,
    ) -> Dict:
        platoon_data: Dict[str, Dict] = defaultdict(
            lambda: {
                "tank_ids": set(),
                "zivud_gaps": defaultdict(int),
                "ammo_totals": defaultdict(float),
                "means_gaps": defaultdict(int),
                "issues": [],
            }
        )

        filters = []
        params: List[str] = []
        target_week = week or (self.latest_week() if prefer_latest else None)
        if target_week:
            filters.append("week_label = ?")
            params.append(target_week)

        query = "SELECT platoon, tank_id, week_label, fields_json FROM form_responses"
        if filters:
            query += " WHERE " + " AND ".join(filters)

        with self.db._connect() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            rows = cur.fetchall()

        for platoon, tank_id, week_label, payload in rows:
            platoon = platoon_override or platoon or "unknown"
            tank_id = self._clean_str(tank_id) or "unknown"
            try:
                fields = json.loads(payload)
            except Exception:
                continue

            data = platoon_data[platoon]
            data["tank_ids"].add(tank_id)
            commander = self._commander_name(fields)

            for field_name, value in fields.items():
                match = self.mapper.match_header(field_name)
                if not match:
                    continue
                if not match.item:
                    continue

                if match.family == "zivud":
                    if self._is_gap(value):
                        data["zivud_gaps"][match.item] += 1
                elif match.family == "ammo":
                    num = self._as_number(value)
                    if num is not None:
                        data["ammo_totals"][match.item] += num
                elif match.family == "means":
                    if self._is_gap(value):
                        data["means_gaps"][match.item] += 1
                elif match.family == "issues":
                    if self._is_issue(value):
                        data["issues"].append(
                            {
                                "item": match.item,
                                "detail": str(value),
                                "tank_id": tank_id,
                                "week": week_label,
                                "commander": commander,
                            }
                        )
                elif match.family == "parsim":
                    text = self._clean_str(value)
                    if text:
                        data["issues"].append(
                            {
                                "item": "פערי צלמים",
                                "detail": text,
                                "tank_id": tank_id,
                                "week": week_label,
                                "commander": commander,
                            }
                        )

        platoon_summaries: Dict[str, PlatoonSummary] = {}
        for platoon, pdata in platoon_data.items():
            tank_count = len(pdata["tank_ids"]) or 0
            ammo_summary: Dict[str, Dict[str, Optional[float]]] = {}
            for item, total in pdata["ammo_totals"].items():
                avg = total / tank_count if tank_count else None
                ammo_summary[item] = {"total": total, "avg_per_tank": avg}

            means_summary: Dict[str, Dict[str, Optional[float]]] = {}
            for item, count in pdata["means_gaps"].items():
                avg = count / tank_count if tank_count else None
                means_summary[item] = {"count": count, "avg_per_tank": avg}

            platoon_summaries[platoon] = PlatoonSummary(
                platoon=platoon,
                week=week,
                tank_count=tank_count,
                zivud_gaps=dict(pdata["zivud_gaps"]),
                ammo=ammo_summary,
                means=means_summary,
                issues=pdata["issues"],
            )

        battalion_zivud = {
            platoon: sum(summary.zivud_gaps.values()) for platoon, summary in platoon_summaries.items()
        }
        battalion_ammo_totals: Dict[str, float] = defaultdict(float)
        battalion_means_totals: Dict[str, int] = defaultdict(int)
        total_tanks = 0
        for summary in platoon_summaries.values():
            total_tanks += summary.tank_count
            for item, metrics in summary.ammo.items():
                battalion_ammo_totals[item] += metrics["total"]
            for item, metrics in summary.means.items():
                battalion_means_totals[item] += metrics["count"]
        battalion_ammo = {
            item: {
                "total": total,
                "avg_per_tank": (total / total_tanks) if total_tanks else None,
            }
            for item, total in battalion_ammo_totals.items()
        }
        battalion_means = {
            item: {
                "count": total,
                "avg_per_tank": (total / total_tanks) if total_tanks else None,
            }
            for item, total in battalion_means_totals.items()
        }

        return {
            "week": target_week,
            "platoons": platoon_summaries,
            "battalion": {
                "zivud_gaps": battalion_zivud,
                "ammo": battalion_ammo,
                "means": battalion_means,
                "tank_count": total_tanks,
            },
        }

    def summarize_platoon(self, platoon: str, week: Optional[str] = None) -> Optional[PlatoonSummary]:
        data = self.summarize(week=week)["platoons"]
        return data.get(platoon)

    @staticmethod
    def serialize_platoon(summary: PlatoonSummary) -> Dict[str, Any]:
        return {
            "platoon": summary.platoon,
            "week": summary.week,
            "tank_count": summary.tank_count,
            "zivud_gaps": summary.zivud_gaps,
            "ammo": summary.ammo,
            "means": summary.means,
            "issues": summary.issues,
        }

    def serialize_summary(self, summary: Dict[str, Any]) -> Dict[str, Any]:
        platoons_serialized = {name: self.serialize_platoon(ps) for name, ps in summary.get("platoons", {}).items()}
        return {
            "week": summary.get("week"),
            "platoons": platoons_serialized,
            "battalion": summary.get("battalion"),
        }

    def _is_gap(self, value) -> bool:
        if value is None:
            return False
        if isinstance(value, (int, float)):
            return False
        text = str(value).strip()
        return any(token in text for token in self.gap_tokens)

    def _is_issue(self, value) -> bool:
        if value is None:
            return False
        if isinstance(value, (int, float)):
            return False
        text = str(value).strip()
        # Consider it an issue if it does not clearly state an OK token
        return not any(tok in text for tok in self.ok_tokens)

    def _commander_name(self, fields: Dict[str, str]) -> Optional[str]:
        return self.mapper.extract_commander(fields)

    @staticmethod
    def _as_number(value) -> Optional[float]:
        try:
            if isinstance(value, bool):
                return None
            if value is None or value == "":
                return None
            return float(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _clean_str(value) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
