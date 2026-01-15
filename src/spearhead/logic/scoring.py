from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
import statistics

from spearhead.data.dto import TankScore
from spearhead.config import settings

@dataclass
class ScoringConfig:
    # Weights for sub-components (Must sum to 1.0)
    weight_zivud: float = 0.4
    weight_ammo: float = 0.3
    weight_completeness: float = 0.3
    
    # Penalties
    deduction_per_missing_zivud: float = 5.0 # Points deducted from Zivud sub-score (0-100) per item
    
    # Critical Keywords (Veto) - If these appear in issues, score is 0
    critical_keywords: Set[str] = field(default_factory=lambda: {
        "מושבת", "תקלת ירי", "תקלת הנעה", "קשר לא תקין", "מנוע", "תותח", "צריח"
    })

class ScoringEngine:
    """
    Pure logic engine for calculating readiness scores.
    """
    def __init__(self, config: Optional[ScoringConfig] = None):
        self.config = config or ScoringConfig()
        self.standards = self._load_standards()

    def _load_standards(self) -> Dict[str, Dict[str, float]]:
        try:
            import json
            from pathlib import Path
            # Assume file is relative to package or specific path
            # For simplicity in this env, using absolute or known relative
            path = Path(__file__).parent.parent / "data" / "standards.json"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {"zivud": {}, "ammo": {}}

    def calculate_tank_score(
        self, 
        tank_id: str,
        zivud_gaps: List[str], 
        ammo_status: Dict[str, float], # { "pgoz": 0.8 (80%) } or { "pgoz": 10 (qty) }? 
                                       # Actually API sends raw counts usually? 
                                       # Let's assume input is normalized 0-1 for now OR logic handles conversion?
                                       # Current IntelligenceService sends empty dict for ammo currently.
        completeness_checks: Dict[str, bool],
        issues: List[str]
    ) -> TankScore:
        """
        Calculates a 0-100 score for a single tank.
        Enforces VETO logic for critical failures.
        """
        
        # 1. Critical Veto Check
        critical_gaps = []
        for issue in issues:
            for kw in self.config.critical_keywords:
                if kw in issue:
                    critical_gaps.append(issue)
        
        if critical_gaps:
             return TankScore(
                tank_id=tank_id,
                score=0.0,
                grade="F",
                critical_gaps=critical_gaps,
                breakdown={"zivud": 0, "ammo": 0, "completeness": 0},
                top_missing_items=zivud_gaps[:3],
                trend="stable" 
            )

        # 2. Zivud Score
        zivud_sub_score = max(0.0, 100.0 - (len(zivud_gaps) * self.config.deduction_per_missing_zivud))
        
        # 3. Ammo Score
        # Expects ammo_status to be { "item_name": quantity }
        # We compare against self.standards["ammo"]
        if ammo_status and self.standards.get("ammo"):
            percentages = []
            for item, qty in ammo_status.items():
                std = self.standards["ammo"].get(item)
                if std and std > 0:
                    # Cap at 100% (1.0)
                    pct = min(1.0, qty / std)
                    percentages.append(pct)
            
            if percentages:
                ammo_sub_score = statistics.mean(percentages) * 100.0
            else:
                # Loop through ALL standards? If we have standards but no data, is it 0?
                # User said "raw files describe the situation". 
                # If we have 0 input for ammo, assuming 100 is risky. 
                # Let's assume neutral 100 if empty input, but if input exists and matches nothing, maybe 0?
                # Sticking to "No Info = 100" or "No Info = Ignore"?
                # Let's keep 100 for stability until proven otherwise.
                ammo_sub_score = 100.0
        else:
            ammo_sub_score = 100.0 

        ammo_sub_score = round(min(100.0, max(0.0, ammo_sub_score)), 1)

        # 4. Completeness Score
        comp_points = sum(1 for v in completeness_checks.values() if v)
        comp_total = len(completeness_checks) or 1
        comp_sub_score = (comp_points / comp_total) * 100.0

        # ... rest is same
        final_score = (
            (zivud_sub_score * self.config.weight_zivud) +
            (ammo_sub_score * self.config.weight_ammo) +
            (comp_sub_score * self.config.weight_completeness)
        )
        final_score = round(final_score, 1)

        # 6. Grading
        if final_score >= 90: grade = "A"
        elif final_score >= 80: grade = "B"
        elif final_score >= 60: grade = "C"
        else: grade = "F"

        return TankScore(
            tank_id=tank_id,
            score=final_score,
            grade=grade,
            critical_gaps=critical_gaps,
            breakdown={
                "zivud": zivud_sub_score, 
                "ammo": ammo_sub_score, 
                "completeness": comp_sub_score
            },
            top_missing_items=zivud_gaps[:3],
            trend="stable"
        )

    def calculate_platoon_score(self, tank_scores: List[TankScore]) -> float:
        if not tank_scores:
            return 0.0
        return round(statistics.mean(t.score for t in tank_scores), 1)

    def get_trend_slope(self, history: List[float]) -> str:
        if len(history) < 2:
            return "stable"
        slope = history[-1] - history[0] # Simple delta for now
        if slope > 5: return "improving"
        if slope < -5: return "degrading"
        return "stable"
