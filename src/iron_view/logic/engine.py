from typing import List
from iron_view.domain.models import BattalionData
from iron_view.logic.analyzers import Analyzer
import logging

logger = logging.getLogger(__name__)

class AnalysisEngine:
    def __init__(self, analyzers: List[Analyzer]):
        self.analyzers = analyzers

    def run(self, data: BattalionData) -> None:
        """
        Runs all registered analyzers on the battalion data.
        """
        logger.info(f"AnalysisEngine: Running {len(self.analyzers)} analyzers...")
        
        # 1. Pre-process: Group by vehicle
        reports_by_vehicle = {}
        for report in data.reports:
            reports_by_vehicle.setdefault(report.vehicle_id, []).append(report)

        # 2. Analyze each vehicle
        for vehicle_id, reports in reports_by_vehicle.items():
            # Sort by time is critical for history analysis
            reports.sort(key=lambda r: r.timestamp)
            
            for analyzer in self.analyzers:
                try:
                    analyzer.analyze(vehicle_id, reports, data)
                except Exception as e:
                    logger.error(f"Analyzer '{analyzer.name}' failed for vehicle {vehicle_id}: {e}")
