from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class Airlock:
    """
    The Airlock ensures no PII (Personally Identifiable Information) 
    enters the processing layer.
    """
    
    FORBIDDEN_COLUMNS = {
        "Soldier Name", "soldier_name", "shem_hayal",
        "Phone", "phone", "telephone", "mobile", 
        "Personal ID", "personal_id", "tz", "id_number",
        "Notes", "notes", "hearot" # Free text is dangerous for privacy
    }

    @classmethod
    def sanitize(cls, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Aggressively strips forbidden columns from the raw dataset.
        """
        sanitized_data = []
        dropped_columns_log = set()

        for row in raw_data:
            clean_row = {}
            for key, value in row.items():
                if key is None:
                    # DictReader can produce None for extra columns; skip safely.
                    continue
                if key in cls.FORBIDDEN_COLUMNS:
                    dropped_columns_log.add(key)
                    continue
                
                # Check case-insensitive
                if key.lower() in cls.FORBIDDEN_COLUMNS:
                     dropped_columns_log.add(key)
                     continue
                
                clean_row[key] = value
            sanitized_data.append(clean_row)
            
        if dropped_columns_log:
            logger.info(f"Airlock: Dropped PII/Forbidden columns: {dropped_columns_log}")
            
        return sanitized_data
