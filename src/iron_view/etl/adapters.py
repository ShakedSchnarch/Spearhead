import pandas as pd
from typing import List, Dict, Any
from datetime import datetime
from iron_view.domain.models import VehicleReport, ReadinessStatus, BattalionData
import logging

logger = logging.getLogger(__name__)

class KfirAdapter:
    """
    Adapter for the 'Kfir' Battalion Google/Monday Form (Excel).
    Maps Hebrew questionnaire columns to internal Iron-View schema.
    """
    
    # Column Mapping (Hebrew -> Internal Concept)
    # Using partial matching keys for robustness
    COL_MAP = {
        "timestamp": "חותמת זמן",
        "vehicle_id": ["מספר צלימו", "צלימו", "מספר צלי"], 
        "company": ["בחר פלוגה", "פלוגה"],
        "status": ["סטטוס לרק\"ם", "סטטוס"], # Escaped quotes
        "location": "מיקום",
        "fault_desc": ["תאר את תקלת הטנ\"א", "תקלת טנא"],
    }

    @classmethod
    def load(cls, file_path: str) -> BattalionData:
        logger.info(f"KfirAdapter: Loading {file_path}")
        try:
            df = pd.read_excel(file_path)
        except Exception as e:
            raise ValueError(f"Failed to read Excel: {e}")

        # Normalize columns (strip whitespace)
        df.columns = df.columns.str.strip()
        
        # Identify exact column names
        cols = cls._resolve_columns(df)
        
        reports = []
        for _, row in df.iterrows():
            try:
                report = cls._parse_row(row, cols)
                if report:
                    reports.append(report)
            except Exception as e:
                logger.warning(f"Skipping row due to error: {e}")
                continue
                
        logger.info(f"KfirAdapter: Parsed {len(reports)} valid reports")
        return BattalionData(reports=reports)

    @classmethod
    def _resolve_columns(cls, df) -> Dict[str, str]:
        """Finds the actual column names in the dataframe based on potential keys."""
        mapping = {}
        df_cols = list(df.columns)
        
        for key, candidates in cls.COL_MAP.items():
            if isinstance(candidates, str):
                candidates = [candidates]
            
            found = False
            for cand in candidates:
                for col in df_cols:
                    # Strict match or specific prefix for robust identification
                    # We want to avoid matching "Location" inside "Mag 1: Location..."
                    if col == cand or col.strip() == cand: 
                        mapping[key] = col
                        found = True
                        break
                    # Special case for Vehicle ID which might be "מספר צלימו"
                    if key == 'vehicle_id' and cand in col and len(col) < 15:
                         mapping[key] = col
                         found = True
                         break
                if found: break
            
            if not found and key in ['timestamp', 'vehicle_id', 'status']:
                 # Critical columns
                 logger.warning(f"Critical column '{key}' not found in {df_cols}")
        
        return mapping

    @classmethod
    def _parse_row(cls, row, cols: Dict[str, str]) -> VehicleReport:
        # 1. ID & Timestamp
        vid = str(row.get(cols.get('vehicle_id'), "UNKNOWN")).strip()
        ts_val = row.get(cols.get('timestamp'))
        
        if pd.isna(ts_val):
            ts = datetime.now()
        else:
            ts = pd.to_datetime(ts_val)

        # 2. Status Mapping
        raw_status = str(row.get(cols.get('status'), "")).strip()
        if "תקין" in raw_status:
            status = ReadinessStatus.OPERATIONAL
        elif "תקול" in raw_status or "מושבת" in raw_status:
            status = ReadinessStatus.UNAVAILABLE
        else:
            status = ReadinessStatus.DEGRADED

        # 3. Faults
        faults = []
        raw_fault = str(row.get(cols.get('fault_desc'), "")).strip()
        if raw_fault and raw_fault not in ["nan", "None", "-"]:
            faults.append(raw_fault)

        # 4. Logistics (Harder, iterating all cols looking for keywords?)
        # For MVP phase 6, we'll scan the row for "תקול" / "חוסר" in columns NOT in the main list
        logistics = []
        for col_name, val in row.items():
            val_str = str(val)
            if "תקול" in val_str or "חסר" in val_str:
                # If column has "מה הצ'" or similar logistics keyword
                if "מה הצ" in col_name or "תקלות" in col_name:
                    # Extract item name from col name (e.g., "מאג 1: ...")
                    item = col_name.split(":")[0].strip()
                    logistics.append(item)
        
        logistics_str = ", ".join(logistics) if logistics else None

        # Generate ID if needed
        report_id = f"{vid}-{int(ts.timestamp())}"

        return VehicleReport(
            report_id=report_id,
            vehicle_id=vid,
            timestamp=ts,
            readiness=status,
            location=str(row.get(cols.get('location'), "Unknown")),
            fault_codes=faults,
            logistics_gap=logistics_str,
            company=str(row.get(cols.get('company'), "Unknown"))
        )
