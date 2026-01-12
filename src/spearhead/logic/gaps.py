import re
from typing import List, Dict, Any
from spearhead.data.dto import GapReport, FormResponseRow

class GapAnalyzer:
    """
    Analyzes form responses to detect operational gaps.
    """
    
    # Regex patterns for negative indicators
    MISSING_PATTERNS = [
        r"חסר", r"אין", r"נגמר", r"לא קיים", r"0", r"^0$"
    ]
    
    WEAR_PATTERNS = [
        r"בלאי", r"תקול", r"שבור", r"קרוע", r"פג תוקף"
    ]

    def __init__(self):
        self.missing_re = re.compile("|".join(self.MISSING_PATTERNS), re.IGNORECASE)
        self.wear_re = re.compile("|".join(self.WEAR_PATTERNS), re.IGNORECASE)

    def analyze_row(self, row: FormResponseRow) -> List[GapReport]:
        """
        Scans all fields in a row for gap indicators.
        """
        gaps = []
        for field, value in row.fields.items():
            val_str = str(value).strip()
            if not val_str:
                continue

            gap_type = None
            if self.missing_re.search(val_str):
                gap_type = "MISSING"
            elif self.wear_re.search(val_str):
                gap_type = "WEAR"

            if gap_type:
                gaps.append(GapReport(
                    platoon=row.platoon or "Unknown",
                    tank_id=row.tank_id or "Unknown",
                    item_name=field,
                    gap_type=gap_type,
                    quantity=1, # Default to 1 unless parsed
                    week=row.week_label or "current"
                ))
        return gaps

    def analyze_batch(self, rows: List[FormResponseRow]) -> List[GapReport]:
        all_gaps = []
        for row in rows:
            all_gaps.extend(self.analyze_row(row))
        return all_gaps
