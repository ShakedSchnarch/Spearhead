from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Optional

import pandas as pd

from spearhead.data.storage import Database
from spearhead.v1.models import MetricSnapshotV2, NormalizedResponseV2


class ResponseStore:
    """
    Persistence layer for responses-only v1 API.
    Backed by SQLite in local/dev. Firestore adapter can be added behind the same interface.
    """

    def __init__(self, db: Database):
        self.db = db
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self.db._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS raw_form_events_v2 (
                    event_id TEXT PRIMARY KEY,
                    schema_version TEXT NOT NULL,
                    source_id TEXT,
                    received_at TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_detail TEXT,
                    created_at TEXT NOT NULL
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS normalized_responses_v2 (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL,
                    source_id TEXT,
                    platoon_key TEXT NOT NULL,
                    tank_id TEXT NOT NULL,
                    week_id TEXT NOT NULL,
                    received_at TEXT NOT NULL,
                    fields_json TEXT NOT NULL,
                    unmapped_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(event_id)
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS metric_snapshots_v2 (
                    snapshot_key TEXT PRIMARY KEY,
                    scope TEXT NOT NULL,
                    dimensions_json TEXT NOT NULL,
                    values_json TEXT NOT NULL,
                    computed_at TEXT NOT NULL
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS ingestion_dlq_v2 (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT,
                    source_id TEXT,
                    payload_json TEXT,
                    error_detail TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_norm_week_platoon ON normalized_responses_v2 (week_id, platoon_key);"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_norm_tank_week ON normalized_responses_v2 (tank_id, week_id);"
            )
            conn.commit()

    def upsert_raw_event(
        self,
        event_id: str,
        schema_version: str,
        source_id: Optional[str],
        received_at: datetime,
        payload_hash: str,
        payload: dict[str, Any],
    ) -> bool:
        payload_json = json.dumps(payload, ensure_ascii=False, default=str)
        now = datetime.now(UTC).isoformat()
        with self.db._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT event_id FROM raw_form_events_v2 WHERE event_id = ?",
                (event_id,),
            )
            if cur.fetchone():
                return False
            cur.execute(
                """
                INSERT INTO raw_form_events_v2
                    (event_id, schema_version, source_id, received_at, payload_hash, payload_json, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'ingested', ?)
                """,
                (
                    event_id,
                    schema_version,
                    source_id,
                    received_at.isoformat(),
                    payload_hash,
                    payload_json,
                    now,
                ),
            )
            conn.commit()
        return True

    def mark_event_status(self, event_id: str, status: str, error_detail: Optional[str] = None) -> None:
        with self.db._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE raw_form_events_v2 SET status = ?, error_detail = ? WHERE event_id = ?",
                (status, error_detail, event_id),
            )
            conn.commit()

    def insert_dlq(self, event_id: Optional[str], source_id: Optional[str], payload: dict[str, Any], error_detail: str) -> None:
        with self.db._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO ingestion_dlq_v2
                    (event_id, source_id, payload_json, error_detail, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    source_id,
                    json.dumps(payload, ensure_ascii=False, default=str),
                    error_detail,
                    datetime.now(UTC).isoformat(),
                ),
            )
            conn.commit()

    def upsert_normalized(self, response: NormalizedResponseV2) -> None:
        with self.db._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT OR REPLACE INTO normalized_responses_v2
                    (event_id, source_id, platoon_key, tank_id, week_id, received_at, fields_json, unmapped_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    response.event_id,
                    response.source_id,
                    response.platoon_key,
                    response.tank_id,
                    response.week_id,
                    response.received_at.isoformat(),
                    json.dumps(response.fields, ensure_ascii=False, default=str),
                    json.dumps(response.unmapped_fields, ensure_ascii=False),
                    datetime.now(UTC).isoformat(),
                ),
            )
            conn.commit()

    def list_normalized(self, week_id: Optional[str] = None, platoon_key: Optional[str] = None) -> list[dict[str, Any]]:
        query = (
            "SELECT event_id, source_id, platoon_key, tank_id, week_id, received_at, fields_json, unmapped_json "
            "FROM normalized_responses_v2 WHERE 1=1"
        )
        params: list[Any] = []
        if week_id:
            query += " AND week_id = ?"
            params.append(week_id)
        if platoon_key:
            query += " AND lower(platoon_key) = lower(?)"
            params.append(platoon_key)
        query += " ORDER BY received_at DESC"

        with self.db._connect() as conn:
            df = pd.read_sql_query(query, conn, params=params)

        if df.empty:
            return []

        rows: list[dict[str, Any]] = []
        for row in df.to_dict("records"):
            row["fields"] = self._safe_json(row.pop("fields_json"), {})
            row["unmapped_fields"] = self._safe_json(row.pop("unmapped_json"), [])
            rows.append(row)
        return rows

    def list_weeks(self, platoon_key: Optional[str] = None) -> list[str]:
        query = "SELECT DISTINCT week_id FROM normalized_responses_v2 WHERE week_id IS NOT NULL"
        params: list[Any] = []
        if platoon_key:
            query += " AND lower(platoon_key) = lower(?)"
            params.append(platoon_key)
        query += " ORDER BY week_id DESC"
        with self.db._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [str(r[0]) for r in rows if r and r[0]]

    def upsert_metric_snapshot(self, snapshot: MetricSnapshotV2) -> None:
        snapshot_key = self._snapshot_key(snapshot.scope, snapshot.dimensions)
        with self.db._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT OR REPLACE INTO metric_snapshots_v2
                    (snapshot_key, scope, dimensions_json, values_json, computed_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    snapshot_key,
                    snapshot.scope,
                    json.dumps(snapshot.dimensions, ensure_ascii=False, sort_keys=True),
                    json.dumps(snapshot.values, ensure_ascii=False, default=str),
                    snapshot.computed_at.isoformat(),
                ),
            )
            conn.commit()

    def get_metric_snapshot(self, scope: str, dimensions: dict[str, str]) -> Optional[dict[str, Any]]:
        snapshot_key = self._snapshot_key(scope, dimensions)
        with self.db._connect() as conn:
            row = conn.execute(
                "SELECT scope, dimensions_json, values_json, computed_at FROM metric_snapshots_v2 WHERE snapshot_key = ?",
                (snapshot_key,),
            ).fetchone()
        if not row:
            return None
        return {
            "scope": row[0],
            "dimensions": self._safe_json(row[1], {}),
            "values": self._safe_json(row[2], {}),
            "computed_at": row[3],
        }

    @staticmethod
    def _snapshot_key(scope: str, dimensions: dict[str, str]) -> str:
        # Stable key to ensure snapshot overwrite per dimension set.
        return f"{scope}:{json.dumps(dimensions, ensure_ascii=False, sort_keys=True)}"

    @staticmethod
    def _safe_json(raw: str, fallback: Any) -> Any:
        try:
            return json.loads(raw)
        except Exception:
            return fallback
