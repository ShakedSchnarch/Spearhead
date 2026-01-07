import json
import sqlite3
from datetime import datetime, UTC
from pathlib import Path
from typing import Iterable, Optional

from iron_view.data.dto import TabularRecord, FormResponseRow


class Database:
    """
    Thin wrapper over sqlite3 for IronView data persistence.
    Keeps schema creation and batch inserts in one place.
    """

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self):
        return sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)

    def _ensure_schema(self):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS imports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    import_key TEXT UNIQUE,
                    source_file TEXT,
                    source_type TEXT,
                    created_at TEXT
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS tabular_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    import_id INTEGER,
                    section TEXT,
                    item TEXT,
                    column_name TEXT,
                    value_text TEXT,
                    value_num REAL,
                    row_index INTEGER,
                    platoon TEXT,
                    FOREIGN KEY (import_id) REFERENCES imports(id)
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS form_responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    import_id INTEGER,
                    row_index INTEGER,
                    tank_id TEXT,
                    timestamp TEXT,
                    fields_json TEXT,
                    FOREIGN KEY (import_id) REFERENCES imports(id)
                );
                """
            )
            conn.commit()

    def upsert_import(self, import_key: str, source_file: Path, source_type: str) -> tuple[int, bool]:
        """
        Idempotent insert: returns (import_id, created_flag).
        """
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM imports WHERE import_key = ?", (import_key,))
            row = cur.fetchone()
            if row:
                return row[0], False
            cur.execute(
                "INSERT INTO imports (import_key, source_file, source_type, created_at) VALUES (?, ?, ?, ?)",
                (
                    import_key,
                    str(source_file),
                    source_type,
                    datetime.now(UTC).isoformat(),
                ),
            )
            conn.commit()
            return cur.lastrowid, True

    def insert_tabular_records(self, import_id: int, records: Iterable[TabularRecord]) -> int:
        to_insert = [
            (
                import_id,
                r.section,
                r.item,
                r.column,
                self._as_text(r.value),
                self._as_number(r.value),
                r.row_index,
                r.platoon,
            )
            for r in records
        ]
        if not to_insert:
            return 0
        with self._connect() as conn:
            cur = conn.cursor()
            cur.executemany(
                """
                INSERT INTO tabular_records
                    (import_id, section, item, column_name, value_text, value_num, row_index, platoon)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                to_insert,
            )
            conn.commit()
            return cur.rowcount

    def insert_form_responses(self, import_id: int, responses: Iterable[FormResponseRow]) -> int:
        to_insert = []
        for r in responses:
            ts = r.timestamp.isoformat() if r.timestamp else None
            # Ensure JSON-serializable payload
            serializable_fields = {}
            for k, v in r.fields.items():
                if isinstance(v, (str, int, float, bool)) or v is None:
                    serializable_fields[k] = v
                elif hasattr(v, "isoformat"):
                    serializable_fields[k] = v.isoformat()
                else:
                    serializable_fields[k] = str(v)
            to_insert.append(
                (
                    import_id,
                    r.row_index,
                    r.tank_id,
                    ts,
                    json.dumps(serializable_fields, ensure_ascii=False),
                )
            )
        if not to_insert:
            return 0
        with self._connect() as conn:
            cur = conn.cursor()
            cur.executemany(
                """
                INSERT INTO form_responses
                    (import_id, row_index, tank_id, timestamp, fields_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                to_insert,
            )
            conn.commit()
            return cur.rowcount

    @staticmethod
    def _as_text(value):
        if value is None:
            return None
        return str(value)

    @staticmethod
    def _as_number(value) -> Optional[float]:
        try:
            if value is None:
                return None
            return float(value)
        except (ValueError, TypeError):
            return None
