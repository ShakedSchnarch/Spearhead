from typing import List
from spearhead.domain.models import VehicleReport, ReadinessStatus

def calculate_erosion_score(history: List[VehicleReport]) -> float:
    """
    Calculates an 'erosion score' indicating the degradation trends of a vehicle.
    
    The score is a value between 0.0 and 1.0, where 1.0 means severe erosion (frequent issues)
    and 0.0 means perfect health history.

    Algorithm:
    - Weighted average of non-OPERATIONAL statuses in the history.
    - Recent reports have higher weight? For v1, let's keep it simple: ratio of bad reports.

    Args:
        history: List of historical reports.

    Returns:
        Float score between 0.0 (Good) and 1.0 (Bad).
    """
    if not history:
        return 0.0

    bad_status_count = sum(
        1 for report in history 
        if report.readiness != ReadinessStatus.OPERATIONAL
    )

    return float(bad_status_count) / len(history)
