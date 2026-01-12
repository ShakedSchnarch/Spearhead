from typing import List, Dict
from spearhead.data.dto import TrendPoint

class TrendAnalyzer:
    """
    Calculates readiness scores over time.
    """
    
    def calculate_trend(self, historical_stats: Dict[str, Dict]) -> List[TrendPoint]:
        """
        Converts a dictionary of {week: stats} into a sorted list of TrendPoints.
        Stats expected to have 'gaps_count' and 'total_items'.
        """
        points = []
        for week, stats in historical_stats.items():
            gaps = stats.get("gaps_count", 0)
            total = stats.get("total_items", 100) # Avoid div by zero, assume baseline
            
            # Simple score: 100 - (gaps * weight)
            # This is a naive heuristic, can be refined.
            score = max(0, 100 - (gaps * 2)) 
            
            points.append(TrendPoint(
                week=week,
                score=score,
                gaps=gaps
            ))
            
        return sorted(points, key=lambda p: p.week)
