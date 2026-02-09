from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from typing import Any, Optional

from spearhead.config import settings
from spearhead.config_fields import field_config
from spearhead.data.field_mapper import FieldMapper
from spearhead.v1.models import FormEventV2, IngestionReportV2, MetricSnapshotV2, NormalizedResponseV2
from spearhead.v1.parser import EventValidationError, FormResponseParserV2
from spearhead.v1.store import ResponseStore


class ResponseIngestionServiceV2:
    def __init__(self, store: ResponseStore, parser: FormResponseParserV2, metrics: "ResponseQueryServiceV2"):
        self.store = store
        self.parser = parser
        self.metrics = metrics

    def ingest_event(self, event: FormEventV2) -> IngestionReportV2:
        payload_hash = hashlib.sha256(
            json.dumps(event.payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        event_id = event.event_id or hashlib.sha256(
            f"{event.schema_version}|{event.source_id}|{payload_hash}".encode("utf-8")
        ).hexdigest()
        event.event_id = event_id

        created = self.store.upsert_raw_event(
            event_id=event_id,
            schema_version=event.schema_version,
            source_id=event.source_id,
            received_at=event.received_at,
            payload_hash=payload_hash,
            payload=event.payload,
        )
        if not created:
            existing = self.store.list_normalized()
            week_id = None
            platoon_key = None
            for item in existing:
                if item["event_id"] == event_id:
                    week_id = item["week_id"]
                    platoon_key = item["platoon_key"]
                    break
            return IngestionReportV2(
                event_id=event_id,
                created=False,
                schema_version=event.schema_version,
                source_id=event.source_id,
                week_id=week_id,
                platoon_key=platoon_key,
            )

        try:
            normalized = self.parser.parse(event)
            self.store.upsert_normalized(normalized)
            self.store.mark_event_status(event_id, status="processed")
            self.metrics.refresh_snapshots(week_id=normalized.week_id, platoon_key=normalized.platoon_key)
            return IngestionReportV2(
                event_id=event_id,
                created=True,
                schema_version=event.schema_version,
                source_id=event.source_id,
                week_id=normalized.week_id,
                platoon_key=normalized.platoon_key,
                unmapped_fields=normalized.unmapped_fields,
            )
        except EventValidationError as exc:
            self.store.mark_event_status(event_id, status="invalid", error_detail=str(exc))
            self.store.insert_dlq(event_id=event_id, source_id=event.source_id, payload=event.payload, error_detail=str(exc))
            raise
        except Exception as exc:
            self.store.mark_event_status(event_id, status="failed", error_detail=str(exc))
            self.store.insert_dlq(event_id=event_id, source_id=event.source_id, payload=event.payload, error_detail=str(exc))
            raise


class ResponseQueryServiceV2:
    def __init__(self, store: ResponseStore):
        self.store = store
        self._mapper = FieldMapper()
        gap_source = settings.status_tokens.gap_tokens + field_config.gap_tokens + ["אין", "חסר", "בלאי", "0"]
        self.gap_tokens = tuple(dict.fromkeys(gap_source))

    def refresh_snapshots(self, week_id: Optional[str], platoon_key: Optional[str]) -> None:
        target_week = week_id or self.latest_week()
        if not target_week:
            return

        overview_values = self._compute_overview(target_week, None)
        self.store.upsert_metric_snapshot(
            MetricSnapshotV2(scope="overview", dimensions={"week_id": target_week}, values=overview_values)
        )

        platoons = overview_values.get("platoons", {})
        for platoon in platoons.keys():
            platoon_values = self._compute_overview(target_week, platoon)
            self.store.upsert_metric_snapshot(
                MetricSnapshotV2(
                    scope="platoon",
                    dimensions={"week_id": target_week, "platoon_key": platoon},
                    values=platoon_values,
                )
            )

        if platoon_key:
            self._refresh_tank_snapshot(target_week, platoon_key)
        else:
            for platoon in platoons.keys():
                self._refresh_tank_snapshot(target_week, platoon)

    def _refresh_tank_snapshot(self, week_id: str, platoon_key: str) -> None:
        tank_values = self._compute_tanks(week_id=week_id, platoon_key=platoon_key)
        self.store.upsert_metric_snapshot(
            MetricSnapshotV2(
                scope="tank",
                dimensions={"week_id": week_id, "platoon_key": platoon_key},
                values={"rows": tank_values},
            )
        )

    def latest_week(self) -> Optional[str]:
        weeks = self.store.list_weeks()
        return weeks[0] if weeks else None

    def list_weeks(self, platoon_key: Optional[str] = None) -> list[str]:
        return self.store.list_weeks(platoon_key=platoon_key)

    def overview(self, week_id: Optional[str], platoon_key: Optional[str] = None) -> dict[str, Any]:
        target_week = week_id or self.latest_week()
        if not target_week:
            return {"week_id": None, "reports": 0, "tanks": 0, "total_gaps": 0, "platoons": {}}

        if platoon_key:
            snapshot = self.store.get_metric_snapshot("platoon", {"week_id": target_week, "platoon_key": platoon_key})
        else:
            snapshot = self.store.get_metric_snapshot("overview", {"week_id": target_week})

        if snapshot:
            return {"week_id": target_week, **snapshot["values"]}

        values = self._compute_overview(target_week, platoon_key)
        self.store.upsert_metric_snapshot(
            MetricSnapshotV2(
                scope="platoon" if platoon_key else "overview",
                dimensions={"week_id": target_week, **({"platoon_key": platoon_key} if platoon_key else {})},
                values=values,
            )
        )
        return {"week_id": target_week, **values}

    def platoon_metrics(self, platoon_key: str, week_id: Optional[str]) -> dict[str, Any]:
        target_week = week_id or self.latest_week()
        if not target_week:
            return {"week_id": None, "platoon_key": platoon_key, "reports": 0, "tanks": 0, "total_gaps": 0}
        data = self.overview(target_week, platoon_key=platoon_key)
        data["platoon_key"] = platoon_key
        return data

    def tank_metrics(self, platoon_key: str, week_id: Optional[str]) -> dict[str, Any]:
        target_week = week_id or self.latest_week()
        if not target_week:
            return {"week_id": None, "platoon_key": platoon_key, "rows": []}

        snapshot = self.store.get_metric_snapshot("tank", {"week_id": target_week, "platoon_key": platoon_key})
        if snapshot:
            return {"week_id": target_week, "platoon_key": platoon_key, **snapshot["values"]}

        rows = self._compute_tanks(target_week, platoon_key)
        payload = {"rows": rows}
        self.store.upsert_metric_snapshot(
            MetricSnapshotV2(
                scope="tank",
                dimensions={"week_id": target_week, "platoon_key": platoon_key},
                values=payload,
            )
        )
        return {"week_id": target_week, "platoon_key": platoon_key, **payload}

    def gaps(
        self,
        week_id: Optional[str],
        platoon_key: Optional[str],
        group_by: str = "item",
        limit: int = 100,
    ) -> dict[str, Any]:
        target_week = week_id or self.latest_week()
        rows = self.store.list_normalized(week_id=target_week, platoon_key=platoon_key)
        if not target_week:
            return {"week_id": None, "rows": []}

        counter: Counter[str] = Counter()
        extras: dict[str, dict[str, Any]] = defaultdict(dict)

        for row in rows:
            tank_id = row["tank_id"]
            for field_name, value in row.get("fields", {}).items():
                if not self._is_gap(value):
                    continue
                if group_by == "tank":
                    key = tank_id
                elif group_by == "family":
                    key = self._family_for_field(field_name)
                else:
                    key = self._item_for_field(field_name)
                counter[key] += 1
                if group_by != "tank":
                    extras[key]["tank_id"] = tank_id

        result_rows = []
        for key, count in counter.most_common(limit):
            entry = {"key": key, "gaps": count}
            if key in extras:
                entry.update(extras[key])
            result_rows.append(entry)

        return {"week_id": target_week, "group_by": group_by, "rows": result_rows}

    def trends(
        self,
        metric: str,
        window_weeks: int,
        platoon_key: Optional[str],
    ) -> dict[str, Any]:
        weeks = self.list_weeks(platoon_key=platoon_key)
        if not weeks:
            return {"metric": metric, "rows": []}
        weeks = sorted(weeks)[-max(window_weeks, 1) :]

        rows = []
        for week_id in weeks:
            ov = self.overview(week_id=week_id, platoon_key=platoon_key)
            if metric == "reports":
                val = ov.get("reports", 0)
            elif metric == "distinct_tanks":
                val = ov.get("tanks", 0)
            elif metric == "gap_rate":
                val = ov.get("gap_rate", 0)
            else:
                val = ov.get("total_gaps", 0)
            rows.append({"week_id": week_id, "value": val})

        return {"metric": metric, "rows": rows}

    def search(self, q: str, week_id: Optional[str], platoon_key: Optional[str], limit: int = 50) -> dict[str, Any]:
        target_week = week_id or self.latest_week()
        if not q or len(q.strip()) < 2:
            return {"week_id": target_week, "rows": []}
        query_text = q.strip().lower()

        rows = self.store.list_normalized(week_id=target_week, platoon_key=platoon_key)
        result = []
        for row in rows:
            base_match = query_text in str(row["tank_id"]).lower() or query_text in str(row["platoon_key"]).lower()
            field_hits = []
            for field_name, value in row.get("fields", {}).items():
                value_text = str(value)
                if query_text in field_name.lower() or query_text in value_text.lower():
                    field_hits.append({"field": field_name, "value": value})

            if base_match or field_hits:
                result.append(
                    {
                        "event_id": row["event_id"],
                        "week_id": row["week_id"],
                        "platoon_key": row["platoon_key"],
                        "tank_id": row["tank_id"],
                        "matches": field_hits[:5],
                        "match_count": len(field_hits),
                    }
                )
            if len(result) >= limit:
                break

        return {"week_id": target_week, "q": q, "rows": result}

    def _compute_overview(self, week_id: str, platoon_key: Optional[str]) -> dict[str, Any]:
        rows = self.store.list_normalized(week_id=week_id, platoon_key=platoon_key)
        if not rows:
            return {"reports": 0, "tanks": 0, "total_gaps": 0, "gap_rate": 0.0, "platoons": {}}

        tanks = {r["tank_id"] for r in rows if r.get("tank_id")}
        platoons: dict[str, dict[str, int]] = defaultdict(lambda: {"reports": 0, "tanks": 0, "gaps": 0})
        tank_sets: dict[str, set[str]] = defaultdict(set)
        total_gaps = 0

        for row in rows:
            platoon = row.get("platoon_key") or "Unknown"
            platoons[platoon]["reports"] += 1
            if row.get("tank_id"):
                tank_sets[platoon].add(row["tank_id"])
            row_gaps = self._count_row_gaps(row.get("fields", {}))
            total_gaps += row_gaps
            platoons[platoon]["gaps"] += row_gaps

        for platoon, tank_ids in tank_sets.items():
            platoons[platoon]["tanks"] = len(tank_ids)

        reports = len(rows)
        return {
            "reports": reports,
            "tanks": len(tanks),
            "total_gaps": total_gaps,
            "gap_rate": round((total_gaps / reports), 3) if reports else 0.0,
            "avg_gaps_per_tank": round((total_gaps / len(tanks)), 3) if tanks else 0.0,
            "platoons": dict(platoons),
        }

    def _compute_tanks(self, week_id: str, platoon_key: str) -> list[dict[str, Any]]:
        rows = self.store.list_normalized(week_id=week_id, platoon_key=platoon_key)
        tanks: dict[str, dict[str, Any]] = defaultdict(lambda: {"gaps": 0, "reports": 0, "families": Counter()})
        for row in rows:
            tank_id = row["tank_id"]
            tanks[tank_id]["reports"] += 1
            for field_name, value in row.get("fields", {}).items():
                if not self._is_gap(value):
                    continue
                tanks[tank_id]["gaps"] += 1
                family = self._family_for_field(field_name)
                tanks[tank_id]["families"][family] += 1

        result = []
        for tank_id, values in tanks.items():
            dominant_family = values["families"].most_common(1)[0][0] if values["families"] else "none"
            result.append(
                {
                    "tank_id": tank_id,
                    "reports": values["reports"],
                    "gaps": values["gaps"],
                    "dominant_family": dominant_family,
                }
            )
        result.sort(key=lambda x: (x["gaps"], x["reports"]), reverse=True)
        return result

    def _count_row_gaps(self, fields: dict[str, Any]) -> int:
        count = 0
        for value in fields.values():
            if self._is_gap(value):
                count += 1
        return count

    def _item_for_field(self, field_name: str) -> str:
        match = self._mapper.match_header(field_name)
        return match.item if match and match.item else field_name

    def _family_for_field(self, field_name: str) -> str:
        match = self._mapper.match_header(field_name)
        return match.family if match and match.family else "other"

    def _is_gap(self, value: Any) -> bool:
        if value is None:
            return False
        text = str(value).strip().lower()
        if not text:
            return False
        return any(tok.lower() in text for tok in self.gap_tokens)
