from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any, Optional

from spearhead.v1.models import MetricSnapshotV2, NormalizedCompanyAssetV2, NormalizedResponseV2


class FirestoreResponseStore:
    """
    Firestore-backed v1 responses store.
    Mirrors the ResponseStore interface used by ingestion/query services.
    """

    def __init__(
        self,
        *,
        project_id: Optional[str] = None,
        database: str = "(default)",
        collection_prefix: str = "spearhead_v1",
    ):
        try:
            from google.api_core.exceptions import AlreadyExists
            from google.cloud import firestore
        except Exception as exc:  # pragma: no cover - depends on optional runtime deps
            raise RuntimeError(
                "Firestore backend requested but google-cloud-firestore is not installed"
            ) from exc

        client_kwargs: dict[str, Any] = {}
        if project_id:
            client_kwargs["project"] = project_id
        if database and database != "(default)":
            client_kwargs["database"] = database

        try:
            self._client = firestore.Client(**client_kwargs)
        except TypeError:
            client_kwargs.pop("database", None)
            self._client = firestore.Client(**client_kwargs)

        self._already_exists_exc = AlreadyExists
        self._prefix = str(collection_prefix).strip() or "spearhead_v1"

    def _collection(self, name: str):
        return self._client.collection(f"{self._prefix}_{name}")

    def upsert_raw_event(
        self,
        event_id: str,
        schema_version: str,
        source_id: Optional[str],
        received_at: datetime,
        payload_hash: str,
        payload: dict[str, Any],
    ) -> bool:
        now = datetime.now(UTC).isoformat()
        payload_json = json.dumps(payload, ensure_ascii=False, default=str)
        doc_ref = self._collection("raw_form_events_v2").document(event_id)
        data = {
            "event_id": event_id,
            "schema_version": schema_version,
            "source_id": source_id,
            "received_at": received_at.isoformat(),
            "payload_hash": payload_hash,
            "payload_json": payload_json,
            "status": "ingested",
            "error_detail": None,
            "created_at": now,
        }
        try:
            doc_ref.create(data)
            return True
        except self._already_exists_exc:
            return False

    def mark_event_status(self, event_id: str, status: str, error_detail: Optional[str] = None) -> None:
        doc_ref = self._collection("raw_form_events_v2").document(event_id)
        doc_ref.set({"status": status, "error_detail": error_detail}, merge=True)

    def insert_dlq(self, event_id: Optional[str], source_id: Optional[str], payload: dict[str, Any], error_detail: str) -> None:
        self._collection("ingestion_dlq_v2").add(
            {
                "event_id": event_id,
                "source_id": source_id,
                "payload_json": json.dumps(payload, ensure_ascii=False, default=str),
                "error_detail": error_detail,
                "created_at": datetime.now(UTC).isoformat(),
            }
        )

    def upsert_normalized(self, response: NormalizedResponseV2) -> None:
        self._collection("normalized_responses_v2").document(response.event_id).set(
            {
                "event_id": response.event_id,
                "source_id": response.source_id,
                "platoon_key": response.platoon_key,
                "platoon_key_lower": (response.platoon_key or "").lower(),
                "tank_id": response.tank_id,
                "week_id": response.week_id,
                "received_at": response.received_at.isoformat(),
                "fields": response.fields,
                "unmapped_fields": response.unmapped_fields,
                "created_at": datetime.now(UTC).isoformat(),
            }
        )

    def list_normalized(self, week_id: Optional[str] = None, platoon_key: Optional[str] = None) -> list[dict[str, Any]]:
        query = self._collection("normalized_responses_v2")
        if week_id:
            query = query.where(field_path="week_id", op_string="==", value=week_id)
        if platoon_key:
            query = query.where(
                field_path="platoon_key_lower",
                op_string="==",
                value=str(platoon_key).lower(),
            )

        rows: list[dict[str, Any]] = []
        for doc in query.stream():
            data = doc.to_dict() or {}
            rows.append(
                {
                    "event_id": data.get("event_id") or doc.id,
                    "source_id": data.get("source_id"),
                    "platoon_key": data.get("platoon_key"),
                    "tank_id": data.get("tank_id"),
                    "week_id": data.get("week_id"),
                    "received_at": self._as_iso(data.get("received_at")),
                    "fields": data.get("fields") or {},
                    "unmapped_fields": data.get("unmapped_fields") or [],
                }
            )

        rows.sort(key=lambda r: str(r.get("received_at") or ""), reverse=True)
        return rows

    def list_weeks(self, platoon_key: Optional[str] = None) -> list[str]:
        query = self._collection("normalized_responses_v2")
        if platoon_key:
            query = query.where(
                field_path="platoon_key_lower",
                op_string="==",
                value=str(platoon_key).lower(),
            )
        weeks: set[str] = set()
        for doc in query.stream():
            data = doc.to_dict() or {}
            week = data.get("week_id")
            if week:
                weeks.add(str(week))
        return sorted(weeks, reverse=True)

    def upsert_company_asset(self, response: NormalizedCompanyAssetV2) -> None:
        self._collection("normalized_company_assets_v2").document(response.event_id).set(
            {
                "event_id": response.event_id,
                "source_id": response.source_id,
                "company_key": response.company_key,
                "company_key_lower": (response.company_key or "").lower(),
                "week_id": response.week_id,
                "received_at": response.received_at.isoformat(),
                "fields": response.fields,
                "unmapped_fields": response.unmapped_fields,
                "created_at": datetime.now(UTC).isoformat(),
            }
        )

    def list_company_assets(self, week_id: Optional[str] = None, company_key: Optional[str] = None) -> list[dict[str, Any]]:
        query = self._collection("normalized_company_assets_v2")
        if week_id:
            query = query.where(field_path="week_id", op_string="==", value=week_id)
        if company_key:
            query = query.where(
                field_path="company_key_lower",
                op_string="==",
                value=str(company_key).lower(),
            )

        rows: list[dict[str, Any]] = []
        for doc in query.stream():
            data = doc.to_dict() or {}
            rows.append(
                {
                    "event_id": data.get("event_id") or doc.id,
                    "source_id": data.get("source_id"),
                    "company_key": data.get("company_key"),
                    "week_id": data.get("week_id"),
                    "received_at": self._as_iso(data.get("received_at")),
                    "fields": data.get("fields") or {},
                    "unmapped_fields": data.get("unmapped_fields") or [],
                }
            )

        rows.sort(key=lambda r: str(r.get("received_at") or ""), reverse=True)
        return rows

    def upsert_metric_snapshot(self, snapshot: MetricSnapshotV2) -> None:
        snapshot_key = self._snapshot_key(snapshot.scope, snapshot.dimensions)
        doc_id = self._snapshot_doc_id(snapshot_key)
        self._collection("metric_snapshots_v2").document(doc_id).set(
            {
                "snapshot_key": snapshot_key,
                "scope": snapshot.scope,
                "dimensions": snapshot.dimensions,
                "values": snapshot.values,
                "computed_at": snapshot.computed_at.isoformat(),
            }
        )

    def get_metric_snapshot(self, scope: str, dimensions: dict[str, str]) -> Optional[dict[str, Any]]:
        snapshot_key = self._snapshot_key(scope, dimensions)
        doc_id = self._snapshot_doc_id(snapshot_key)
        doc = self._collection("metric_snapshots_v2").document(doc_id).get()
        if not doc.exists:
            return None
        data = doc.to_dict() or {}
        return {
            "scope": data.get("scope", scope),
            "dimensions": data.get("dimensions") or dimensions,
            "values": data.get("values") or {},
            "computed_at": self._as_iso(data.get("computed_at")),
        }

    @staticmethod
    def _snapshot_key(scope: str, dimensions: dict[str, str]) -> str:
        return f"{scope}:{json.dumps(dimensions, ensure_ascii=False, sort_keys=True)}"

    @staticmethod
    def _snapshot_doc_id(snapshot_key: str) -> str:
        return hashlib.sha256(snapshot_key.encode("utf-8")).hexdigest()

    @staticmethod
    def _as_iso(value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, datetime):
            dt = value if value.tzinfo else value.replace(tzinfo=UTC)
            return dt.isoformat()
        return str(value)
