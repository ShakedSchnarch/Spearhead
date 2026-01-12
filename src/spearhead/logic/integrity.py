from typing import List
from spearhead.domain.models import VehicleReport

def detect_copy_paste(current_report: VehicleReport, history: List[VehicleReport]) -> bool:
    """
    Detects if the current report's notes appear to be copy-pasted from the immediate previous report.

    Args:
        current_report: The report being validated.
        history: A list of past reports for this vehicle.

    Returns:
        True if copy-paste is detected, False otherwise.
    """
    if not history:
        return False

    # Sort history by timestamp descending just to be safe, though usually caller might provide it sorted
    sorted_history = sorted(history, key=lambda x: x.timestamp, reverse=True)
    
    last_report = sorted_history[0]

    # Ignore empty notes
    if not current_report.notes or not last_report.notes:
        return False

    # Check for exact string match on notes
    # In a real system, we might use cosine similarity or Levenshtein distance
    return current_report.notes.strip() == last_report.notes.strip()
