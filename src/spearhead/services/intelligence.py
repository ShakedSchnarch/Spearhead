from typing import List, Optional, Dict
from datetime import datetime, UTC

from spearhead.data.dto import (
    PlatoonIntelligence, 
    TankScore, 
    BattalionIntelligence,
    FormResponseRow,
    TrendPoint,
)
from spearhead.data.repositories import FormRepository
from spearhead.logic.scoring import ScoringEngine
from spearhead.data.field_mapper import FieldMapper
from spearhead.config import settings
import json
import pandas as pd

class IntelligenceService:
    """
    Orchestrates data retrieval and scoring logic to produce high-level intelligence insights.
    Enforces strict tenant isolation.
    """
    def __init__(self, repository: FormRepository, scoring_engine: ScoringEngine):
        self.repo = repository
        self.engine = scoring_engine
        self.mapper = FieldMapper()

    def get_platoon_intelligence(
        self, 
        platoon: str, 
        week: Optional[str] = None
    ) -> PlatoonIntelligence:
        """
        Generates intelligence report for a single platoon.
        """
        # Fetch all history for platoon for trend/delta calculations
        df_all = self.repo.get_forms(platoon=platoon)
        target_week = week or self.repo.get_latest_week() or "Unknown"
        df_current = df_all[df_all["week_label"] == target_week] if not df_all.empty else pd.DataFrame()
        display_platoon = self._display_platoon(platoon)

        # If no data, return empty structure
        if df_current.empty:
            return PlatoonIntelligence(
                platoon=display_platoon, 
                week=target_week, 
                readiness_score=0.0, 
                tank_scores=[], 
                critical_tanks_count=0,
                breakdown={"zivud": 0.0, "ammo": 0.0, "comms": 0.0, "completeness": 0.0},
                deltas={"overall": None},
                coverage={"reports_this_week": 0, "expected": 0, "missing_reports": 0},
                top_gaps_platoon=[],
                top_gaps_battalion_level=[]
            )

        # Compute tank scores for current week
        tank_scores = self._score_dataframe(df_current)
        # Compute trends/deltas using history
        tank_scores = self._attach_trends_and_deltas(tank_scores, df_all)

        # Aggregates
        platoon_score = self.engine.calculate_platoon_score(tank_scores)
        critical_count = sum(1 for t in tank_scores if t.score < 60)
        family_keys = ["zivud", "ammo", "comms", "completeness"]
        breakdown = {
            k: round(sum(t.family_breakdown.get(k, 0) for t in tank_scores) / len(tank_scores), 1)
            for k in family_keys
        }
        # Overall delta from previous week
        prev_week = self._previous_week(target_week, df_all)
        prev_platoon_score = None
        if prev_week:
            prev_df = df_all[df_all["week_label"] == prev_week]
            prev_scores = self._score_dataframe(prev_df)
            prev_platoon_score = self.engine.calculate_platoon_score(prev_scores) if prev_scores else None
        deltas = {"overall": round(platoon_score - prev_platoon_score, 1) if prev_platoon_score is not None else None}

        # Coverage
        reports_this_week = len(df_current)
        expected_tanks = len(df_all["tank_id"].dropna().unique())
        distinct_current = len(df_current["tank_id"].dropna().unique())
        coverage = {
            "reports_this_week": reports_this_week,
            "expected": expected_tanks,
            "missing_reports": max(expected_tanks - distinct_current, 0),
        }

        # Top gaps per platoon
        gap_counter: Dict[str, int] = {}
        for t in tank_scores:
            for g in t.top_missing_items or []:
                gap_counter[g] = gap_counter.get(g, 0) + 1
            for g in t.critical_gaps or []:
                gap_counter[g] = gap_counter.get(g, 0) + 1
        top_gaps_platoon = [
            {"item": item, "gaps": count, "family": "zivud"} for item, count in sorted(gap_counter.items(), key=lambda x: x[1], reverse=True)
        ]

        # Sort priority list
        tank_scores.sort(key=lambda x: x.score)

        return PlatoonIntelligence(
            platoon=display_platoon,
            week=target_week,
            readiness_score=platoon_score,
            tank_scores=tank_scores,
            critical_tanks_count=critical_count,
            top_gaps_battalion_level=[],
            breakdown=breakdown,
            deltas=deltas,
            coverage=coverage,
            top_gaps_platoon=top_gaps_platoon,
        )

    def get_battalion_intelligence(self, week: Optional[str] = None) -> BattalionIntelligence:
        """
        Aggregates intelligence for all platoons.
        """
        # Fetch all platoons
        all_platoons = self.repo.get_unique_values("platoon", week=week)
        platoon_intels = {}
        comparison = {}
        top_gaps_battalion = {}
        
        target_week = week or self.repo.get_latest_week() or "Unknown"

        for p in all_platoons:
            intel = self.get_platoon_intelligence(p, week=target_week)
            display_name = intel.platoon
            platoon_intels[display_name] = intel
            comparison[display_name] = intel.readiness_score
            for gap in intel.top_gaps_platoon or []:
                item = gap["item"]
                top_gaps_battalion.setdefault(item, {})[display_name] = gap["gaps"]

        # Calculate battalion average
        total_score = sum(comparison.values()) / len(comparison) if comparison else 0.0
        top_gaps_list = [{"item": k, "platoons": v} for k, v in top_gaps_battalion.items()]
        
        return BattalionIntelligence(
            week=target_week,
            overall_readiness=round(total_score, 1),
            platoons=platoon_intels,
            comparison=comparison,
            deltas={"overall": None}, # Could be extended later
            top_gaps_battalion=top_gaps_list,
        )

    def _parse_qty(self, val_str: str, standard: float) -> float:
        """
        Parses a quantity string like '36', 'full', 'missing'.
        """
        val_lower = val_str.lower().strip()
        if not val_lower or val_lower in ["nan", "none", ""]:
            return standard # Assume OK if missing? Or 0? 
                            # User says: Raw files have data. If missing, usually implies OK in this domain unless explicit "0".
            return standard

        # Explicit numeric
        try:
            return float(val_lower)
        except:
            pass
        
        # Keywords
        if any(x in val_lower for x in ["מלא", "full", "ok", "takin", "קיים"]):
            return standard
        if any(x in val_lower for x in ["חסר", "missing", "ריק", "empty", "0"]):
            return 0.0
        
        # Heuristics for partials? "Half"?
        if "חצי" in val_lower or "half" in val_lower:
            return standard * 0.5

        # Default fallback
        return standard

    def _is_gap(self, text: str) -> bool:
        # Re-use logic or import? For speed, duplicating basic tokens
        tokens = ["חסר", "אין", "תקול", "בלאי", "0"]
        return any(t in text for t in tokens)

    def _is_issue(self, text: str) -> bool:
         # Anything not 'takin'
         ok_tokens = ["תקין", "יש", "מלא"]
         if any(t in text for t in ok_tokens): return False
         return True

    def _score_dataframe(self, df: pd.DataFrame) -> List[TankScore]:
        """
        Scores all rows (tanks) in the provided dataframe.
        """
        tank_scores: List[TankScore] = []
        for _, row in df.iterrows():
            tank_id = row.get("tank_id")
            if not tank_id:
                continue
            score = self._score_row(row)
            tank_scores.append(score)
        return tank_scores

    def _score_row(self, row: pd.Series) -> TankScore:
        tank_id = row.get("tank_id")
        try:
            fields = json.loads(row.get("fields_json", "{}"))
        except Exception:
            fields = {}

        zivud_gaps = []
        ammo_status = {}
        completeness = {"has_form": True}
        issues = []

        for k, v in fields.items():
            match = self.mapper.match_header(k)
            if not match:
                continue

            val_str = str(v).strip()

            if match.family == "zivud":
                if self._is_gap(val_str):
                    zivud_gaps.append(match.item)

            is_ammo = False
            std_qty = 0.0
            if match.item in self.engine.standards.get("ammo", {}):
                is_ammo = True
                std_qty = self.engine.standards["ammo"][match.item]
            elif match.family == "ammo":
                is_ammo = True
                std_qty = 1.0

            if is_ammo:
                parsed_qty = self._parse_qty(val_str, std_qty)
                ammo_status[match.item] = parsed_qty

            if match.family == "issues" or "תקלה" in k or text_is_critical(val_str):
                if self._is_issue(val_str):
                    issues.append(f"{match.item}: {val_str}")

        score = self.engine.calculate_tank_score(
            tank_id=str(tank_id),
            zivud_gaps=zivud_gaps,
            ammo_status=ammo_status,
            completeness_checks=completeness,
            issues=issues
        )
        # Ensure enriched fields
        score.family_breakdown = {
            "zivud": score.breakdown.get("zivud", 0.0),
            "ammo": score.breakdown.get("ammo", 0.0),
            "comms": score.breakdown.get("completeness", 0.0),  # placeholder until comms parsed separately
            "completeness": score.breakdown.get("completeness", 0.0),
        }
        score.gap_counts = {
            "zivud": len(zivud_gaps),
            "ammo": sum(1 for qty in ammo_status.values() if qty == 0),
            "comms": 0,
        }
        return score

    def _attach_trends_and_deltas(self, tank_scores: List[TankScore], df_all: pd.DataFrame, window: int = 8) -> List[TankScore]:
        if df_all.empty:
            return tank_scores
        # Gather weeks sorted ascending
        weeks = sorted([w for w in df_all.get("week_label", []).dropna().unique()])
        weeks = weeks[-window:] if window else weeks
        # Precompute scores per week per tank
        week_tank_scores: Dict[str, Dict[str, float]] = {}
        for w in weeks:
            df_week = df_all[df_all["week_label"] == w]
            for score in self._score_dataframe(df_week):
                week_tank_scores.setdefault(score.tank_id, {})[w] = score.score

        for score in tank_scores:
            history = week_tank_scores.get(score.tank_id, {})
            trend_points = [TrendPoint(week=w, score=history[w], gaps=0) for w in weeks if w in history]
            score.trend = trend_points
            # Delta vs previous week if exists
            if len(weeks) >= 2 and weeks[-2] in history:
                score.deltas = {"overall": round(score.score - history[weeks[-2]], 1)}
            else:
                score.deltas = {"overall": None}
        return tank_scores

    def _previous_week(self, target_week: str, df_all: pd.DataFrame) -> Optional[str]:
        if df_all.empty or "week_label" not in df_all.columns:
            return None
        weeks = sorted([w for w in df_all["week_label"].dropna().unique()])
        if target_week not in weeks:
            return weeks[-1] if weeks else None
        idx = weeks.index(target_week)
        if idx == 0:
            return None
        return weeks[idx - 1]

    @staticmethod
    def _display_platoon(name: str) -> str:
        aliases = {
            "kfir": "כפיר",
            "mahatz": "מחץ",
            "sufa": "סופה",
        }
        key = (name or "").strip().lower()
        return aliases.get(key, name)

def text_is_critical(text: str) -> bool:
    # Heuristic for veto words in free text
    criticals = ["מושבת", "תקלת ירי", "תקלת הנעה"]
    return any(c in text for c in criticals)
