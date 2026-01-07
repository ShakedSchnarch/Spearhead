from typing import List, Dict, Any
from collections import Counter
from iron_view.domain.models import BattalionData, ReadinessStatus

class DeterministicQueries:
    """
    Fixed business logic queries that are 100% accurate (The 'Iron' Brain).
    Used for KPI cards, priority lists, and structured data feeds.
    """

    @staticmethod
    def get_priority_list(data: BattalionData) -> List[Dict[str, Any]]:
        """
        Returns vehicles that require immediate attention.
        Criteria: Unavailable status OR High AI Severity.
        """
        priority = []
        for r in data.reports:
            severity = r.ai_inference.get('severity_score', 0) if r.ai_inference else 0
            if r.readiness != ReadinessStatus.OPERATIONAL or severity >= 50:
                priority.append({
                    "vehicle_id": r.vehicle_id,
                    "company": r.company,
                    "status": r.readiness.value, # 'UNAVAILABLE', 'DEGRADED'
                    "heb_status": r.readiness.heb,
                    "faults": r.fault_codes,
                    "logistics": r.logistics_gap,
                    "ai_severity": severity,
                    "ai_action": r.ai_inference.get('recommended_action', '-') if r.ai_inference else '-'
                })
        
        # Sort by severity descending
        return sorted(priority, key=lambda x: x['ai_severity'], reverse=True)

    @staticmethod
    def get_logistics_summary(data: BattalionData) -> List[Dict[str, Any]]:
        """Returns aggregated count of missing items."""
        counter = Counter()
        for r in data.reports:
            if r.logistics_gap:
                # Assuming gaps are comma-separated or just single strings.
                # Simple split by comma if needed, for now just counting the raw string if simple.
                items = [i.strip() for i in r.logistics_gap.split(',')]
                counter.update(items)
        
        return [{"item": item, "count": count} for item, count in counter.most_common(5)]


    @staticmethod
    def get_integrity_stats(data: BattalionData) -> int:
        """Returns count of suspicious reports."""
        return sum(1 for r in data.reports if r.integrity_flags)

    @staticmethod
    def get_fault_breakdown(data: BattalionData) -> Dict[str, int]:
        """
        Aggregates faults by category for the Doughnut Chart.
        Simplified logic: 
        - 10-29: Automotive (Mneoa)
        - 30-49: Comm/Elec (Kesher)
        - 50+: Fire Control (Bakar)
        """
        categories = {
            "Automotive": 0,
            "Electronics": 0,
            "Fire Control": 0,
            "Other": 0
        }
        
        for r in data.reports:
            if not r.fault_codes:
                continue
            
            # fault_codes is List[str]
            for code_str in r.fault_codes:
                # Handle potential "10, 20" inside a list item just in case, though it should be split
                sub_codes = [c.strip() for c in code_str.split(',')]
                for code in sub_codes:
                    if code.isdigit():
                        val = int(code)
                        if 10 <= val <= 29:
                            categories["Automotive"] += 1
                        elif 30 <= val <= 49:
                            categories["Electronics"] += 1
                        elif val >= 50:
                            categories["Fire Control"] += 1
                        else:
                            categories["Other"] += 1
                    else:
                        categories["Other"] += 1
                    
        # Remove zero entries to keep chart clean? Or keep for consistency. Keeping all.
        return categories
