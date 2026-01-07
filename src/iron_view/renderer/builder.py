from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from iron_view.domain.models import BattalionData

from iron_view.config import Settings

class ReportBuilder:
    def __init__(self, template_dir: Path, assets_dir: Path, settings: Settings):
        self.template_dir = template_dir
        self.assets_dir = assets_dir
        self.settings = settings
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))

    def build_artifact(self, data: BattalionData) -> str:
        """
        Generates the HTML report by rendering the template with data
        and injecting inline CSS/JS assets.
        """
        template = self.env.get_template("dashboard.j2")
        
        # Read assets
        # We combine Tailwind (for resets/utils) and the configured theme
        theme_file = self.settings.app.theme
        css_content = self._read_asset("tailwind.min.css") + "\n" + self._read_asset(theme_file)
        js_content = self._read_asset("chart.min.js") + "\n" + self._read_asset("dashboard.js")
        
        # Prepare Chart Data (Readiness over Time)
        # 1. Group by date
        from collections import defaultdict
        from datetime import datetime
        daily_counts = defaultdict(int) 
        daily_total = defaultdict(int)
        
        # Simple metric: % of OPERATIONAL vehicles per day
        # Note: This is a rough approximation for v1
        for report in data.reports:
            day = report.timestamp.strftime("%Y-%m-%d")
            daily_total[day] += 1
            if report.readiness == "OPERATIONAL":
                daily_counts[day] += 1
                
        sorted_days = sorted(daily_total.keys())
        chart_labels = sorted_days
        chart_data = []
        for day in sorted_days:
            percentage = (daily_counts[day] / daily_total[day]) * 100 if daily_total[day] > 0 else 0
            chart_data.append(round(percentage, 1))
            
        # Phase 10: Real Chart Data
        # 1. Deterministic
        from iron_view.logic.queries import DeterministicQueries
        priority_list = DeterministicQueries.get_priority_list(data)
        logistics_summary = DeterministicQueries.get_logistics_summary(data)
        integrity_count = DeterministicQueries.get_integrity_stats(data)
        fault_breakdown = DeterministicQueries.get_fault_breakdown(data)

        # 2. Generative (Simulated)
        from iron_view.logic.llm_client import LLMClient
        llm = LLMClient()
        ai_feed = llm.generate_battalion_insight(data)

        # 3. Serialize for Client-Side (JS)
        # Ensure enums are converted to strings and datetimes to ISO
        js_reports = []
        for r in data.reports:
            r_dict = r.dict() if hasattr(r, 'dict') else r.model_dump()
            r_dict['readiness'] = r.readiness.value # Serialize Enum
            if 'timestamp' in r_dict and r_dict['timestamp']:
                 r_dict['timestamp'] = r_dict['timestamp'].isoformat()
            js_reports.append(r_dict)

        now = datetime.now() 

        context = {
            "data": data,
            "now": now,
            "chart_labels": chart_labels,
            "chart_values": chart_data,
            "fault_breakdown": fault_breakdown,
            "js_reports": js_reports, # For Modal
            "css_content": css_content,
            "js_content": js_content,
            "priority_list": priority_list,
            "logistics_summary": logistics_summary,
            "integrity_count": integrity_count,
            "ai_feed": ai_feed,
            "settings": self.settings
        }
        
        return template.render(context)

    def _read_asset(self, filename: str) -> str:
        """Helper to read asset files from the defined assets directory."""
        path = self.assets_dir / filename
        if not path.exists():
            return "" # Return empty if missing to avoid crash
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _load_assets(self) -> tuple[str, str]:
        css = self._read_asset("tactical.css")
        js = self._read_asset("chart.js")
        return css, js
