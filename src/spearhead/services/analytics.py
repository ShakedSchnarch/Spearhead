import json
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, UTC
from typing import Dict, List, Optional, Any, Set

from spearhead.config import settings
from spearhead.config_fields import field_config
from spearhead.data.field_mapper import FieldMapper
from spearhead.data.storage import Database
from spearhead.data.dto import GapReport, FormResponseRow
from spearhead.data.repositories import FormRepository
from spearhead.logic.gaps import GapAnalyzer


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
    Uses Repository Layer for data access to enforce tenant isolation.
    """

    def __init__(self, repository: FormRepository):
        self.repo = repository
        self.mapper = FieldMapper()
        # Extend tokens for common "missing" phrasing
        gap_source = settings.status_tokens.gap_tokens + field_config.gap_tokens + ["אין"]
        ok_source = settings.status_tokens.ok_tokens + field_config.ok_tokens + ["יש", "תקין"]
        # Keep order but drop duplicates
        self.gap_tokens = tuple(dict.fromkeys(gap_source))
        self.ok_tokens = tuple(dict.fromkeys(ok_source))
        self.gap_analyzer = GapAnalyzer()

    @staticmethod
    def _sanitize_week(week_str: Optional[str]) -> Optional[str]:
        if not week_str:
            return None
        # Remove any non-alphanumeric/dash chars (e.g. hidden LTR marks)
        # Keep strictly YYYY-Www format
        import re
        clean = re.sub(r"[^0-9A-Z\-]", "", str(week_str).strip())
        return clean or None

    def get_gaps(self, week: Optional[str] = None, platoon: Optional[str] = None) -> List[GapReport]:
        """
        Returns a detailed list of extracted gaps using the logic engine.
        """
        target_week = self._sanitize_week(week) or self.latest_week()
        
        # Repository handles tenant filtering via 'platoon' arg
        df = self.repo.get_forms(week=target_week, platoon=platoon)
        
        if df.empty:
            return []

        # Convert DataFrame rows to FormResponseRow objects
        response_rows = []
        for _, row in df.iterrows():
            try:
                # Assuming 'fields_json' column exists
                fields = json.loads(row.get("fields_json", "{}"))
            except Exception:
                fields = {}

            response_rows.append(FormResponseRow(
                source_file=None, 
                platoon=row.get("platoon", "unknown"),
                row_index=row.get("row_index", 0),
                tank_id=row.get("tank_id"),
                timestamp=None, # could parse from row.get("timestamp")
                week_label=row.get("week_label"),
                fields=fields
            ))
            
        return self.gap_analyzer.analyze_batch(response_rows)

    def latest_week(self) -> Optional[str]:
        return self.repo.get_latest_week()

    @staticmethod
    def _current_week_label() -> str:
        return datetime.now(UTC).strftime("%Y-W%W")

    def platoons(self, week: Optional[str] = None) -> List[str]:
        target_week = self._sanitize_week(week)
        raw = self.repo.get_unique_values("platoon", week=target_week)
        return sorted(list({self._display_platoon(p) for p in raw}))

    def summarize(
        self,
        week: Optional[str] = None,
        platoon_override: Optional[str] = None,
        prefer_latest: bool = False,
    ) -> Dict:
        target_week = self._sanitize_week(week) or (self.latest_week() if prefer_latest else None)
        
        # If platoon_override is set, we fetch specific. 
        # But 'summarize' usually needs context. 
        # If this service is used by a Battalion user, platoon_override might be None (fetch all).
        # Repository.get_forms(platoon=...) will filter if provided.
        df = self.repo.get_forms(week=target_week, platoon=platoon_override)

        platoon_data: Dict[str, Dict] = defaultdict(
            lambda: {
                "tank_ids": set(),
                "zivud_gaps": defaultdict(int),
                "ammo_totals": defaultdict(float),
                "means_gaps": defaultdict(int),
                "issues": [],
            }
        )

        if not df.empty:
            for _, row in df.iterrows():
                platoon_raw = platoon_override or row.get("platoon") or "unknown"
                platoon = self._display_platoon(platoon_raw)
                tank_id = self._clean_str(row.get("tank_id")) or "unknown"
                week_label = row.get("week_label")
                try:
                    fields = json.loads(row.get("fields_json", "{}"))
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
            "latest_week": self.latest_week() or self._current_week_label(),
            "available_weeks": self.available_weeks(),
            "platoons": platoon_summaries,
            "battalion": {
                "zivud_gaps": battalion_zivud,
                "ammo": battalion_ammo,
                "means": battalion_means,
                "tank_count": total_tanks,
            },
        }

    def summarize_platoon(self, platoon: str, week: Optional[str] = None) -> Optional[PlatoonSummary]:
        data = self.summarize(week=week, platoon_override=platoon)["platoons"]
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
            "latest_week": summary.get("latest_week"),
            "available_weeks": summary.get("available_weeks"),
            "platoons": platoons_serialized,
            "battalion": summary.get("battalion"),
        }

    def available_weeks(self) -> List[str]:
        return self.repo.get_unique_values("week_label")

    def coverage(
        self,
        week: Optional[str] = None,
        window_weeks: int = 4,
        prefer_latest: bool = True,
        platoon: Optional[str] = None,
    ) -> Dict[str, Any]:
        target_week = self._sanitize_week(week) or (self.latest_week() if prefer_latest else None) or self._current_week_label()
        platoon_filter = self._clean_str(platoon)

        # Coverage needs context of all platoons to show who is missing.
        # However, if we are in a 'platoon' scope (Repository restricted), we only see that platoon.
        # That's correct for tenant isolation.
        
        # We need ALL forms to calculate history/last_seen. 
        # So we fetch everything (subject to repository scope).
        # Fetch Global weeks for context (anomaly detection needs full timeline)
        available_weeks = sorted(self.repo.get_unique_values("week_label"), reverse=True)
        
        # Fetch Data (Filtered by repository if platoon provided)
        # This handles Hebrew/English normalization (e.g. כפיר -> Kfir)
        df = self.repo.get_forms(platoon=platoon)
        
        if df.empty:
            return {"week": target_week, "platoons": {}, "anomalies": []}

        week_forms: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        week_tanks: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set))
        last_seen: Dict[str, Optional[datetime]] = defaultdict(lambda: None)

        for _, row in df.iterrows():
            platoon_row = row.get("platoon") or "unknown"
            week_label = row.get("week_label")
            tank_id = row.get("tank_id")
            ts_raw = row.get("timestamp")

            if week_label:
                week_forms[platoon_row][week_label] += 1
                if tank_id:
                    week_tanks[platoon_row][week_label].add(str(tank_id))
            
            if ts_raw:
                try:
                    ts = datetime.fromisoformat(str(ts_raw))
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=UTC)
                except Exception:
                    ts = None
                
                if ts and (last_seen[platoon_row] is None or ts > last_seen[platoon_row]):
                    last_seen[platoon_row] = ts

        coverage: Dict[str, Dict[str, Any]] = {}
        anomalies: List[Dict[str, Any]] = []
        now = datetime.now(UTC)

        for platoon in week_forms.keys():
            display_platoon = self._display_platoon(platoon)
            forms_current = week_forms[platoon].get(target_week, 0)
            tanks_current = len(week_tanks[platoon].get(target_week, set()))
            platoon_last_seen = last_seen.get(platoon)
            days_since_last = (now - platoon_last_seen).days if platoon_last_seen else None

            recent_weeks = [w for w in available_weeks if w != target_week][:window_weeks]
            recent_counts = [week_forms[platoon].get(w, 0) for w in recent_weeks]
            avg_forms_recent = sum(recent_counts) / len(recent_counts) if recent_counts else None

            anomaly_reason = None
            if forms_current == 0:
                anomaly_reason = "no_reports"
            elif avg_forms_recent is not None and forms_current < 0.7 * avg_forms_recent:
                anomaly_reason = "low_volume"
            elif days_since_last is not None and days_since_last > 7:
                anomaly_reason = "stale"

            entry = {
                "week": target_week,
                "forms": forms_current,
                "distinct_tanks": tanks_current,
                "last_seen": platoon_last_seen.isoformat() if platoon_last_seen else None,
                "days_since_last": days_since_last,
                "avg_forms_recent": avg_forms_recent,
                "anomaly": anomaly_reason,
            }
            coverage[display_platoon] = entry
            if anomaly_reason:
                anomalies.append(
                    {
                        "platoon": display_platoon,
                        "week": target_week,
                        "reason": anomaly_reason,
                        "forms": forms_current,
                        "avg_forms_recent": avg_forms_recent,
                        "days_since_last": days_since_last,
                    }
                )

        return {
            "week": target_week,
            "latest_week": self.latest_week() or self._current_week_label(),
            "available_weeks": available_weeks,
            "platoons": coverage,
            "anomalies": anomalies,
        }

    @staticmethod
    def _display_platoon(name: str) -> str:
        aliases = {
            "kfir": "כפיר",
            "mahatz": "מחץ",
            "sufa": "סופה",
        }
        key = (name or "").strip().lower()
        return aliases.get(key, name)

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
