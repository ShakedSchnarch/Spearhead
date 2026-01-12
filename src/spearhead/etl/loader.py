import csv
import logging
from pathlib import Path
from typing import List, Optional

from pydantic import ValidationError

from spearhead.domain.models import VehicleReport, BattalionData, ReadinessStatus
from spearhead.exceptions import DataSourceError

logger = logging.getLogger(__name__)

def load_data(file_path: Path) -> BattalionData:
    """
    Loads vehicle reports from a CSV file.
    Skips corrupt rows and logs errors.
    """
    logger.info(f"Loading data from {file_path}")
    
    # Phase 6: Adapter Support
    if str(file_path).endswith('.xlsx'):
        from spearhead.etl.adapters import KfirAdapter
        try:
            return KfirAdapter.load(str(file_path))
        except Exception as e:
             raise DataSourceError(f"Adapter failed: {e}")

    # Fallback to CSV
    if not file_path.exists():
        logger.error(f"Input file not found: {file_path}")
        raise DataSourceError(f"Input file not found: {file_path}")

    with open(file_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        raw_rows = list(reader)

    # 1. Privacy Airlock
    from spearhead.etl.airlock import Airlock
    safe_rows = Airlock.sanitize(raw_rows)

    reports: List[VehicleReport] = []
    for row_num, row in enumerate(safe_rows, start=1):
            try:
                # Basic cleaning
                cleaned_row = {k: v.strip() if isinstance(v, str) else v for k, v in row.items() if v}
                
                # Convert readiness string to Enum
                if 'readiness' in cleaned_row and cleaned_row['readiness']:
                    try:
                        cleaned_row['readiness'] = ReadinessStatus(cleaned_row['readiness'].upper())
                    except ValueError:
                        pass
                
                # Handle comma-separated fault codes
                if 'fault_codes' in cleaned_row and isinstance(cleaned_row['fault_codes'], str):
                    cleaned_row['fault_codes'] = [f.strip() for f in cleaned_row['fault_codes'].split(',') if f.strip()]

                # Generate a report_id if missing (essential for internals)
                if 'report_id' not in cleaned_row:
                    # Create a deterministic ID based on vehicle + time
                    ts_str = cleaned_row.get('timestamp', '')
                    vid = cleaned_row.get('vehicle_id', 'unknown')
                    cleaned_row['report_id'] = f"{vid}-{ts_str.replace(' ', '_').replace(':', '')}"

                report = VehicleReport(**cleaned_row)
                reports.append(report)
            except (ValidationError, ValueError) as e:
                logger.warning(f"Skipping corrupt row {row_num}: {e}. Data: {row}")
            except Exception as e:
                logger.error(f"Unexpected error on row {row_num}: {e}")

    return BattalionData(reports=reports)
