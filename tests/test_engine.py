import pytest
from spearhead.logic.engine import AnalysisEngine
from spearhead.logic.analyzers import Analyzer
from spearhead.domain.models import BattalionData, VehicleReport, ReadinessStatus
from datetime import datetime

class MockAnalyzer:
    name = "mock"
    def analyze(self, vehicle_id, reports, data):
        data.vehicle_scores[vehicle_id] = 99.9

def test_engine_runs_analyzers():
    data = BattalionData(reports=[
        VehicleReport(
            report_id="1", vehicle_id="v1", timestamp=datetime.now(), 
            readiness=ReadinessStatus.OPERATIONAL, reporter="u"
        )
    ])
    
    engine = AnalysisEngine([MockAnalyzer()])
    engine.run(data)
    
    assert data.vehicle_scores["v1"] == 99.9

def test_engine_handles_exception_in_analyzer(caplog):
    class BadAnalyzer:
        name = "bad"
        def analyze(self, vehicle_id, reports, data):
            raise ValueError("Boom")

    data = BattalionData(reports=[
        VehicleReport(
            report_id="1", vehicle_id="v1", timestamp=datetime.now(), 
            readiness=ReadinessStatus.OPERATIONAL, reporter="u"
        )
    ])
    
    engine = AnalysisEngine([BadAnalyzer()])
    engine.run(data)
    
    assert "Analyzer 'bad' failed for vehicle v1: Boom" in caplog.text
