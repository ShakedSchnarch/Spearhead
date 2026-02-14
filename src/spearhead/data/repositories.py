from typing import List, Optional, Protocol, TypeVar, Generic
from pydantic import BaseModel
import pandas as pd
from spearhead.data.storage import Database
from spearhead.exceptions import DataSourceError

T = TypeVar("T", bound=BaseModel)

class Repository(Protocol, Generic[T]):
    def get_all(self, scope: Optional[str] = None) -> List[T]:
        """Retrieve all items, optionally filtered by scope (platoon/tenant)."""
        ...

class BaseRepository:
    def __init__(self, db: Database):
        self.db = db

    def apply_scope(self, df: pd.DataFrame, scope: Optional[str] = None, column: str = "Platoon") -> pd.DataFrame:
        """
        Applies tenant isolation (scoping) to a DataFrame.
        If scope is None or 'battalion' or 'all', no filter is applied (subject to authorization layer).
        If scope is a specific platoon name, filters the DataFrame.
        """
        if not scope or scope in ("battalion", "all", ""):
            return df
        
        if column not in df.columns:
            # Try case-insensitive lookup for robustness
            alt = {c.lower(): c for c in df.columns}.get(column.lower())
            if alt:
                column = alt
            else:
                return pd.DataFrame(columns=df.columns)

        # Normalize scope to canonical English key (e.g. "כפיר" -> "Kfir")
        target_scope = self._normalize_platoon(scope)
        
        # Build list of all valid raw values that map to this target
        # This handles mixed data (some rows "Kfir", some "כפיר")
        valid_values = {target_scope.lower()}
        for alias, canonical in self._alias_map.items():
            if canonical == target_scope:
                valid_values.add(alias.lower())
        
        # Also include the raw input just in case
        valid_values.add(str(scope).strip().lower())

        # Normalize column for comparison
        col_norm = df[column].fillna("").astype(str).str.strip().str.lower()
        
        return df[col_norm.isin(valid_values)]

    @property
    def _alias_map(self) -> dict:
        return {
            "כפיר": "Kfir",
            "kfir": "Kfir",
            "kphir": "Kfir", # Mentioned in user screenshot?
            "מחץ": "Mahatz",
            "mahatz": "Mahatz",
            "machatz": "Mahatz",
            "סופה": "Sufa",
            "sufa": "Sufa",
            "פלס״מ": "Palsam",
            'פלס"ם': "Palsam",
            "פלסמ": "Palsam",
            "פלסם": "Palsam",
            "palsam": "Palsam",
            "romach": "battalion",
            "רומח": "battalion",
            "גדוד": "battalion",
            "battalion": "battalion",
        }

    @staticmethod
    def _normalize_platoon(name: Optional[str]) -> str:
        """
        Maps common platoon aliases (Hebrew/English/case) to canonical labels stored in DB.
        """
        if not name:
            return ""
        raw = str(name).strip()
        lower = raw.lower()
        # Use simple map or shared property
        # We need an instance to access property, but this method is static.
        # Let's duplicate or make property static-friendly.
        # Quick fix: Hardcode here to avoid breaking staticmethod signature in interface.
        alias_map = {
            "כפיר": "Kfir",
            "kfir": "Kfir",
            "kphir": "Kfir",
            "מחץ": "Mahatz",
            "mahatz": "Mahatz",
            "machatz": "Mahatz",
            "סופה": "Sufa",
            "sufa": "Sufa",
            "פלס״מ": "Palsam",
            'פלס"ם': "Palsam",
            "פלסמ": "Palsam",
            "פלסם": "Palsam",
            "palsam": "Palsam",
            "romach": "battalion",
            "רומח": "battalion",
            "גדוד": "battalion",
            "battalion": "battalion",
        }
        return alias_map.get(lower, raw)

class FormRepository(BaseRepository):
    """
    Repository for accessing Form Responses (Raw Data).
    Table: 'form_responses'
    """
    def __init__(self, db: Database):
        super().__init__(db)
        self.table = "form_responses"

    def get_forms(self, 
                  week: Optional[str] = None, 
                  platoon: Optional[str] = None) -> pd.DataFrame:
        """
        Fetch form responses with optional filtering.
        Enforces tenant isolation via 'platoon' arg.
        """
        # 1. Fetch Raw Data
        # Optimization: In a real SQL DB, we would filter in the WHERE clause.
        # Here we use pandas over the full table (SQLite/Parquet abstraction).
        try:
            df = self.db.read_table(self.table)
        except Exception as e:
            # Table might not exist yet
            return pd.DataFrame()

        if df.empty:
            return df

        # 2. Apply Logical Filters (Date/Week)
        if week:
            week_cols = {c.lower(): c for c in df.columns}
            target_week_col = week_cols.get("week_label") or week_cols.get("week")
            if target_week_col:
                df = df[df[target_week_col] == week]

        # 3. Apply Tenant Isolation (Security Scope)
        # Persisted column name is lowercase 'platoon'
        df = self.apply_scope(df, scope=platoon, column="platoon")
        
        return df

    def get_latest_sync_metadata(self) -> dict:
        """Return metadata about the last sync operation."""
        return {}

    def get_latest_week(self) -> Optional[str]:
        """Fetch the most recent week label from the data."""
        df = self.get_forms()
        if not df.empty and "week_label" in df.columns:
            # Drop nulls and sort
            weeks = df["week_label"].dropna().unique()
            if len(weeks) > 0:
                return sorted(weeks)[-1]
        return None

    def get_unique_values(self, column: str, week: Optional[str] = None) -> List[str]:
        """Get distinct values for a column (e.g., 'platoon', 'week_label')."""
        df = self.get_forms(week=week)
        if df.empty or column not in df.columns:
            return []
        
        values = df[column].dropna().unique().tolist()
        return sorted([str(v) for v in values])

class TabularRepository(BaseRepository):
    """
    Repository for accessing Tabular Records (Ammo, Zivud, etc).
    Table: 'tabular_records' joined with 'imports'
    """
    def __init__(self, db: Database):
        super().__init__(db)
        self.table = "tabular_records"

    def get_records(self, section: str, week: Optional[str] = None, platoon: Optional[str] = None) -> pd.DataFrame:
        """
        Fetch tabular records joined with import metadata.
        Filters by section (required), week, and platoon (tenant).
        """
        # Construct SQL for efficient joining and filtering
        # We manually construct the week_label using SQLite strftime
        query = """
        SELECT t.*, i.created_at, strftime('%Y-W%W', datetime(i.created_at)) as week_label
        FROM tabular_records t
        JOIN imports i ON t.import_id = i.id
        WHERE t.section = ?
        """
        params = [section]

        # Note: We filter by week in SQL if possible, but SQLite logic for generated column in WHERE 
        # might be tricky without a subquery or repeating the expression.
        # Repeating expression is safe.
        if week:
            query += " AND strftime('%Y-W%W', datetime(i.created_at)) = ?"
            params.append(week)
            
        # Platoon Scope
        if platoon:
             query += " AND t.platoon = ?"
             params.append(platoon)

        try:
            with self.db._connect() as conn:
                df = pd.read_sql_query(query, conn, params=params)
        except Exception:
            return pd.DataFrame()
            
        return df

    def get_latest_imports(self, section: str, limit: int = 1) -> List[int]:
        """Get IDs of latest imports for a section."""
        query = """
        SELECT imports.id
        FROM imports
        JOIN tabular_records ON tabular_records.import_id = imports.id
        WHERE tabular_records.section = ?
        GROUP BY imports.id
        ORDER BY imports.created_at DESC
        LIMIT ?
        """
        try:
            with self.db._connect() as conn:
                df = pd.read_sql_query(query, conn, params=[section, limit])
                return df["id"].tolist() if not df.empty else []
        except Exception:
            return []

    def get_totals_by_import(self, section: str, import_id: int) -> pd.DataFrame:
        """Get aggregated totals for a specific import ID."""
        query = """
        SELECT item, SUM(COALESCE(value_num, 0)) as total_num
        FROM tabular_records
        WHERE section = ? AND import_id = ?
        GROUP BY item
        """
        try:
            with self.db._connect() as conn:
                df = pd.read_sql_query(query, conn, params=[section, import_id])
                return df
        except Exception:
            return pd.DataFrame()
