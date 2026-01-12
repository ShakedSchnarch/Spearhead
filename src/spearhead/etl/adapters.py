import pandas as pd
from typing import List, Dict, Any
from datetime import datetime
from spearhead.domain.models import VehicleReport, ReadinessStatus, BattalionData
import logging

logger = logging.getLogger(__name__)

class KfirAdapter:
    """
    Adapter for the 'Kfir' Battalion Google/Monday Form (Excel).
    Maps Hebrew questionnaire columns to internal Spearhead schema.
    """
    
    # Column Mapping (Hebrew -> Internal Concept)
    # Using partial matching keys for robustness
    COL_MAP = {
        "timestamp": "חותמת זמן",
        "vehicle_id": ["צ טנק", "מספר צלימו", "צלימו", "מספר צלי"], 
        "company": ["בחר פלוגה", "פלוגה", "מחלקה"], # Added 'Mahlaka' just in case
        "status": ["אוק", "סטטוס לרק\"ם", "סטטוס", "מצב כשירו"], 
        "location": ["מיקום", "מיקום הטנק"],
        "fault_desc": ["מה הבלאי", "תאר את תקלת הטנ\"א", "תקלת טנא"],
    }

    @classmethod
    def load(cls, file_path: str) -> BattalionData:
        logger.info(f"KfirAdapter: Loading {file_path}")
        try:
            df = pd.read_excel(file_path)
        except Exception as e:
            raise ValueError(f"Failed to read Excel: {e}")

        # Normalize columns (strip whitespace)
        df.columns = df.columns.astype(str).str.strip()
        
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
        
        return mapping

    @classmethod
    def _parse_row(cls, row, cols: Dict[str, str]) -> VehicleReport:
        # 1. ID & Timestamp
        # Support "צ טנק"
        vid_col = cols.get('vehicle_id')
        vid = str(row.get(vid_col, "UNKNOWN")).strip() if vid_col else "UNKNOWN"
        
        ts_col = cols.get('timestamp')
        ts_val = row.get(ts_col)
        
        if pd.isna(ts_val):
            ts = datetime.now()
        else:
            try:
                ts = pd.to_datetime(ts_val)
            except:
                ts = datetime.now()

        # 2. Status Mapping
        status_col = cols.get('status')
        if status_col:
            raw_status = str(row.get(status_col, "")).strip()
            if "תקין" in raw_status or "אוק" in raw_status or "OK" in raw_status.upper():
                 status = ReadinessStatus.OPERATIONAL
            elif "תקול" in raw_status or "מושבת" in raw_status:
                 status = ReadinessStatus.UNAVAILABLE
            else:
                 # Default to operational if empty? No, Degraded?
                 # If "אוק" column has values like "V" or "X", we need to know.
                 # Assuming "Gap" form usually implies issues if filled?
                 status = ReadinessStatus.OPERATIONAL # Optimistic default
        else:
            status = ReadinessStatus.OPERATIONAL # Default if no status col

        # 3. Faults
        faults = []
        fault_col = cols.get('fault_desc')
        if fault_col:
            raw_fault = str(row.get(fault_col, "")).strip()
            if raw_fault and raw_fault not in ["nan", "None", "-", "0"]:
                faults.append(raw_fault)

        # 4. Logistics
        logistics = []
        for col_name, val in row.items():
            val_str = str(val)
            # Logic: If column name contains "דוח זיווד" and value implies missing
            if "דוח זיווד" in col_name:
                # Check for specific "missing" indicators accurately
                # "0" should be standalone or explicit boolean false. 
                # "לא" should be standalone.
                # "חסר" can be part of string.
                v_lower = val_str.lower()
                is_gap = False
                
                if "חסר" in v_lower or "לא תקין" in v_lower:
                    is_gap = True
                elif val_str.strip() == "0" or val_str.strip() == "לא":
                    is_gap = True
                elif "x" in v_lower and len(v_lower) < 5: # e.g. "X" mark
                    is_gap = True
                
                if is_gap:
                    # Extract item
                    item_raw = col_name.replace("דוח זיווד", "").replace("[", "").replace("]", "").strip()
                    logistics.append(item_raw)

            # Also catch generic "missing" tokens in other columns (like Logistics Status)
            if "חסר" in val_str or "תקול" in val_str:
                 if ":" in col_name:
                     logistics.append(col_name.split(":")[0])

        logistics_str = ", ".join(logistics) if logistics else None

        # Generate ID
        report_id = f"{vid}-{int(ts.timestamp())}"

        # Company: Default to 'כפיר' if not found
        comp_col = cols.get('company')
        company = str(row.get(comp_col, "כפיר")).strip() if comp_col else "כפיר"

        return VehicleReport(
            report_id=report_id,
            vehicle_id=vid,
            timestamp=ts,
            readiness=status,
            location=str(row.get(cols.get('location'), "Unknown")),
            fault_codes=faults,
            logistics_gap=logistics_str,
            company=company
        )
