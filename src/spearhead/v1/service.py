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
        configured_sections = settings.operational.sections or ["Armament", "Logistics", "Communications"]
        self.sections = [str(section).strip() for section in configured_sections if str(section).strip()]
        if not self.sections:
            self.sections = ["Armament", "Logistics", "Communications"]
        self._section_lookup = {section.lower(): section for section in self.sections}

        family_map = settings.operational.family_to_section or {}
        mapped: dict[str, str] = {}
        for family, section in family_map.items():
            canonical = self._canonical_section(section)
            if canonical:
                mapped[str(family).strip().lower()] = canonical
        self.family_to_section = mapped

        configured_display = settings.operational.section_display_names or {}
        self.section_display_names = {
            section: configured_display.get(section, section)
            for section in self.sections
        }
        configured_notes = settings.operational.section_scope_notes or {}
        self.section_scope_notes = {
            section: configured_notes.get(section, "")
            for section in self.sections
        }

        critical_items = settings.operational.critical_item_names or []
        self.critical_items = [str(item).strip() for item in critical_items if str(item).strip()]
        self.critical_item_lookup = {
            self._normalize_item_name(item): item
            for item in self.critical_items
        }
        try:
            penalty = float(settings.operational.critical_gap_penalty)
        except Exception:
            penalty = 12.0
        self.critical_gap_penalty = max(0.0, penalty)

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

    def battalion_sections_view(self, week_id: Optional[str], platoon_scope: Optional[str] = None) -> dict[str, Any]:
        target_week = week_id or self.latest_week()
        if not target_week:
            return {
                "week_id": None,
                "previous_week_id": None,
                "scope": platoon_scope,
                "sections": list(self.sections),
                "section_display_names": self.section_display_names,
                "section_scope_notes": self.section_scope_notes,
                "companies": [],
                "rows": [],
            }

        current_rows = self.store.list_normalized(week_id=target_week, platoon_key=platoon_scope)
        previous_week = self._previous_week(target_week, platoon_scope)
        previous_rows = self.store.list_normalized(week_id=previous_week, platoon_key=platoon_scope) if previous_week else []

        current_metrics = self._compute_section_metrics(current_rows)
        previous_metrics = self._compute_section_metrics(previous_rows)

        companies = sorted(
            {
                company
                for company, _ in current_metrics.keys() | previous_metrics.keys()
            }
        )
        if platoon_scope and platoon_scope not in companies:
            companies.append(platoon_scope)
            companies = sorted(companies)

        rows: list[dict[str, Any]] = []
        for company in companies:
            for section in self.sections:
                current = current_metrics.get((company, section), self._empty_section_metrics(company, section))
                previous = previous_metrics.get((company, section), self._empty_section_metrics(company, section))
                rows.append(
                    {
                        **current,
                        "delta_gaps": current["total_gaps"] - previous["total_gaps"],
                        "delta_gap_rate": round(current["gap_rate"] - previous["gap_rate"], 3),
                        "delta_reports": current["reports"] - previous["reports"],
                        "delta_tanks": current["tanks"] - previous["tanks"],
                        "delta_readiness": self._score_delta(
                            current.get("readiness_score"),
                            previous.get("readiness_score"),
                        ),
                        "delta_critical_gaps": current.get("critical_gaps", 0) - previous.get("critical_gaps", 0),
                    }
                )

        return {
            "week_id": target_week,
            "previous_week_id": previous_week,
            "scope": platoon_scope,
            "sections": list(self.sections),
            "section_display_names": self.section_display_names,
            "section_scope_notes": self.section_scope_notes,
            "companies": companies,
            "rows": rows,
        }

    def company_sections_view(self, company_key: str, week_id: Optional[str]) -> dict[str, Any]:
        target_week = week_id or self.latest_week()
        company = company_key
        if not target_week:
            return {
                "week_id": None,
                "previous_week_id": None,
                "company": company,
                "sections": [],
                "reports": 0,
                "tanks": 0,
                "readiness_score": None,
                "critical_tanks": 0,
                "section_display_names": self.section_display_names,
                "section_scope_notes": self.section_scope_notes,
            }

        current_rows = self.store.list_normalized(week_id=target_week, platoon_key=company)
        previous_week = self._previous_week(target_week, company)
        previous_rows = self.store.list_normalized(week_id=previous_week, platoon_key=company) if previous_week else []

        current_metrics = self._compute_section_metrics(current_rows)
        previous_metrics = self._compute_section_metrics(previous_rows)
        top_items = self._top_gap_items_by_section(current_rows)
        top_critical_items = self._top_critical_items_by_section(current_rows)

        section_rows: list[dict[str, Any]] = []
        for section in self.sections:
            current = current_metrics.get((company, section), self._empty_section_metrics(company, section))
            previous = previous_metrics.get((company, section), self._empty_section_metrics(company, section))
            section_rows.append(
                {
                    **current,
                    "delta_gaps": current["total_gaps"] - previous["total_gaps"],
                    "delta_gap_rate": round(current["gap_rate"] - previous["gap_rate"], 3),
                    "delta_reports": current["reports"] - previous["reports"],
                    "delta_tanks": current["tanks"] - previous["tanks"],
                    "delta_readiness": self._score_delta(
                        current.get("readiness_score"),
                        previous.get("readiness_score"),
                    ),
                    "delta_critical_gaps": current.get("critical_gaps", 0) - previous.get("critical_gaps", 0),
                    "top_gap_items": top_items.get(section, []),
                    "top_critical_items": top_critical_items.get(section, []),
                }
            )

        reports = len(current_rows)
        tanks = len({row.get("tank_id") for row in current_rows if row.get("tank_id")})
        company_tanks = self._compute_tank_overall_metrics(current_rows)
        company_summary = self._aggregate_company_readiness(company_tanks.values())

        return {
            "week_id": target_week,
            "previous_week_id": previous_week,
            "company": company,
            "reports": reports,
            "tanks": tanks,
            "readiness_score": company_summary["avg_readiness"],
            "critical_tanks": company_summary["critical_tanks"],
            "section_display_names": self.section_display_names,
            "section_scope_notes": self.section_scope_notes,
            "sections": section_rows,
        }

    def company_section_tanks_view(self, company_key: str, section: str, week_id: Optional[str]) -> dict[str, Any]:
        target_week = week_id or self.latest_week()
        company = company_key
        resolved_section = self._canonical_section(section)
        if not resolved_section:
            raise ValueError(f"Unknown section '{section}'")

        if not target_week:
            return {
                "week_id": None,
                "previous_week_id": None,
                "company": company,
                "section": resolved_section,
                "section_display_name": self.section_display_names.get(resolved_section, resolved_section),
                "section_scope_note": self.section_scope_notes.get(resolved_section, ""),
                "rows": [],
            }

        current_rows = self.store.list_normalized(week_id=target_week, platoon_key=company)
        previous_week = self._previous_week(target_week, company)
        previous_rows = self.store.list_normalized(week_id=previous_week, platoon_key=company) if previous_week else []

        current_metrics = self._compute_tank_section_metrics(current_rows, resolved_section)
        previous_metrics = self._compute_tank_section_metrics(previous_rows, resolved_section)

        result_rows = []
        for tank_id, current in current_metrics.items():
            previous = previous_metrics.get(
                tank_id,
                {"gaps": 0, "checked_items": 0, "reports": 0, "critical_gaps": 0, "readiness_score": None},
            )
            gaps = current["gaps"]
            critical_gaps = current.get("critical_gaps", 0)
            status = "Critical" if critical_gaps > 0 else ("OK" if gaps == 0 else "Gap")
            result_rows.append(
                {
                    "tank_id": tank_id,
                    "status": status,
                    "reports": current["reports"],
                    "checked_items": current["checked_items"],
                    "gaps": gaps,
                    "delta_gaps": gaps - previous.get("gaps", 0),
                    "critical_gaps": critical_gaps,
                    "delta_critical_gaps": critical_gaps - previous.get("critical_gaps", 0),
                    "readiness_score": current.get("readiness_score"),
                    "delta_readiness": self._score_delta(
                        current.get("readiness_score"),
                        previous.get("readiness_score"),
                    ),
                    "gap_items": current.get("gap_items", []),
                    "critical_items": current.get("critical_items", []),
                }
            )

        result_rows.sort(
            key=lambda row: (
                row.get("critical_gaps", 0),
                row.get("gaps", 0),
                self._sort_readiness_key(row.get("readiness_score")),
                row.get("reports", 0),
                row.get("tank_id", ""),
            ),
            reverse=True,
        )
        return {
            "week_id": target_week,
            "previous_week_id": previous_week,
            "company": company,
            "section": resolved_section,
            "section_display_name": self.section_display_names.get(resolved_section, resolved_section),
            "section_scope_note": self.section_scope_notes.get(resolved_section, ""),
            "rows": result_rows,
        }

    def company_tanks_view(self, company_key: str, week_id: Optional[str]) -> dict[str, Any]:
        target_week = week_id or self.latest_week()
        company = company_key
        if not target_week:
            return {
                "week_id": None,
                "previous_week_id": None,
                "company": company,
                "section_display_names": self.section_display_names,
                "section_scope_notes": self.section_scope_notes,
                "summary": {
                    "tanks": 0,
                    "avg_readiness": None,
                    "critical_tanks": 0,
                    "critical_items": [],
                },
                "rows": [],
            }

        current_rows = self.store.list_normalized(week_id=target_week, platoon_key=company)
        previous_week = self._previous_week(target_week, company)
        previous_rows = self.store.list_normalized(week_id=previous_week, platoon_key=company) if previous_week else []

        current_metrics = self._compute_tank_overall_metrics(current_rows)
        previous_metrics = self._compute_tank_overall_metrics(previous_rows)
        summary = self._aggregate_company_readiness(current_metrics.values())

        rows: list[dict[str, Any]] = []
        for tank_id in sorted(current_metrics.keys()):
            current = current_metrics[tank_id]
            previous = previous_metrics.get(tank_id, {})

            per_section = current.get("sections", {})
            rows.append(
                {
                    "tank_id": tank_id,
                    "status": "Critical" if current.get("critical_gaps", 0) > 0 else ("Gap" if current.get("gaps", 0) > 0 else "OK"),
                    "reports": current.get("reports", 0),
                    "checked_items": current.get("checked_items", 0),
                    "gaps": current.get("gaps", 0),
                    "critical_gaps": current.get("critical_gaps", 0),
                    "critical_items": current.get("critical_items", []),
                    "readiness_score": current.get("readiness_score"),
                    "delta_readiness": self._score_delta(
                        current.get("readiness_score"),
                        previous.get("readiness_score"),
                    ),
                    "delta_gaps": current.get("gaps", 0) - previous.get("gaps", 0),
                    "sections": per_section,
                    "logistics_readiness": self._section_score_value(per_section, "Logistics"),
                    "armament_readiness": self._section_score_value(per_section, "Armament"),
                    "communications_readiness": self._section_score_value(per_section, "Communications"),
                }
            )

        rows.sort(
            key=lambda row: (
                row.get("critical_gaps", 0),
                self._sort_readiness_key(row.get("readiness_score")),
                row.get("gaps", 0),
                row.get("tank_id", ""),
            ),
            reverse=True,
        )

        return {
            "week_id": target_week,
            "previous_week_id": previous_week,
            "company": company,
            "section_display_names": self.section_display_names,
            "section_scope_notes": self.section_scope_notes,
            "summary": summary,
            "rows": rows,
        }

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

    def _compute_section_metrics(self, rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
        companies = sorted({row.get("platoon_key") or "Unknown" for row in rows})
        metrics: dict[tuple[str, str], dict[str, Any]] = {}
        for company in companies:
            for section in self.sections:
                metrics[(company, section)] = {
                    "company": company,
                    "section": section,
                    "reports": 0,
                    "tanks_set": set(),
                    "checked_items": 0,
                    "total_gaps": 0,
                    "critical_gaps": 0,
                }

        for row in rows:
            company = row.get("platoon_key") or "Unknown"
            tank_id = str(row.get("tank_id") or "").strip()
            per_section = defaultdict(lambda: {"checked_items": 0, "gaps": 0, "critical_gaps": 0})

            for field_name, value in row.get("fields", {}).items():
                section = self._section_for_field(field_name)
                if not section:
                    continue
                item_name = self._item_for_field(field_name)
                per_section[section]["checked_items"] += 1
                if self._is_gap(value):
                    per_section[section]["gaps"] += 1
                    if self._is_critical_item(item_name):
                        per_section[section]["critical_gaps"] += 1

            for section, counts in per_section.items():
                entry = metrics.setdefault(
                    (company, section),
                    {
                        "company": company,
                        "section": section,
                        "reports": 0,
                        "tanks_set": set(),
                        "checked_items": 0,
                        "total_gaps": 0,
                        "critical_gaps": 0,
                    },
                )
                entry["reports"] += 1
                if tank_id:
                    entry["tanks_set"].add(tank_id)
                entry["checked_items"] += counts["checked_items"]
                entry["total_gaps"] += counts["gaps"]
                entry["critical_gaps"] += counts.get("critical_gaps", 0)

        finalized: dict[tuple[str, str], dict[str, Any]] = {}
        for key, values in metrics.items():
            reports = values["reports"]
            tanks_count = len(values["tanks_set"])
            readiness_score = self._compute_readiness_score(
                checked_items=values["checked_items"],
                gaps=values["total_gaps"],
                critical_gaps=values.get("critical_gaps", 0),
            )
            finalized[key] = {
                "company": values["company"],
                "section": values["section"],
                "reports": reports,
                "tanks": tanks_count,
                "checked_items": values["checked_items"],
                "total_gaps": values["total_gaps"],
                "critical_gaps": values.get("critical_gaps", 0),
                "gap_rate": round((values["total_gaps"] / reports), 3) if reports else 0.0,
                "readiness_score": readiness_score,
            }
        return finalized

    def _compute_tank_section_metrics(self, rows: list[dict[str, Any]], section: str) -> dict[str, dict[str, Any]]:
        metrics: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "reports": 0,
                "checked_items": 0,
                "gaps": 0,
                "critical_gaps": 0,
                "gap_items": Counter(),
                "critical_items": Counter(),
            }
        )

        for row in rows:
            tank_id = str(row.get("tank_id") or "").strip()
            if not tank_id:
                continue

            has_section_data = False
            for field_name, value in row.get("fields", {}).items():
                if self._section_for_field(field_name) != section:
                    continue
                has_section_data = True
                item_name = self._item_for_field(field_name)
                metrics[tank_id]["checked_items"] += 1
                if self._is_gap(value):
                    metrics[tank_id]["gaps"] += 1
                    metrics[tank_id]["gap_items"][item_name] += 1
                    if self._is_critical_item(item_name):
                        metrics[tank_id]["critical_gaps"] += 1
                        metrics[tank_id]["critical_items"][item_name] += 1

            if has_section_data:
                metrics[tank_id]["reports"] += 1

        finalized: dict[str, dict[str, Any]] = {}
        for tank_id, values in metrics.items():
            finalized[tank_id] = {
                "reports": values["reports"],
                "checked_items": values["checked_items"],
                "gaps": values["gaps"],
                "critical_gaps": values["critical_gaps"],
                "readiness_score": self._compute_readiness_score(
                    checked_items=values["checked_items"],
                    gaps=values["gaps"],
                    critical_gaps=values["critical_gaps"],
                ),
                "gap_items": [
                    {"item": item, "gaps": count}
                    for item, count in values["gap_items"].most_common(10)
                ],
                "critical_items": [
                    {"item": item, "gaps": count}
                    for item, count in values["critical_items"].most_common(10)
                ],
            }
        return finalized

    def _top_gap_items_by_section(self, rows: list[dict[str, Any]], limit: int = 5) -> dict[str, list[dict[str, Any]]]:
        counters: dict[str, Counter[str]] = {section: Counter() for section in self.sections}
        for row in rows:
            for field_name, value in row.get("fields", {}).items():
                if not self._is_gap(value):
                    continue
                section = self._section_for_field(field_name)
                if not section:
                    continue
                counters.setdefault(section, Counter())[self._item_for_field(field_name)] += 1
        return {
            section: [{"item": item, "gaps": gaps} for item, gaps in counter.most_common(limit)]
            for section, counter in counters.items()
        }

    def _top_critical_items_by_section(self, rows: list[dict[str, Any]], limit: int = 5) -> dict[str, list[dict[str, Any]]]:
        counters: dict[str, Counter[str]] = {section: Counter() for section in self.sections}
        for row in rows:
            for field_name, value in row.get("fields", {}).items():
                if not self._is_gap(value):
                    continue
                section = self._section_for_field(field_name)
                if not section:
                    continue
                item_name = self._item_for_field(field_name)
                if self._is_critical_item(item_name):
                    counters.setdefault(section, Counter())[item_name] += 1
        return {
            section: [{"item": item, "gaps": gaps} for item, gaps in counter.most_common(limit)]
            for section, counter in counters.items()
        }

    def _compute_tank_overall_metrics(self, rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        metrics: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "reports": 0,
                "checked_items": 0,
                "gaps": 0,
                "critical_gaps": 0,
                "gap_items": Counter(),
                "critical_items": Counter(),
                "sections": {
                    section: {
                        "reports": 0,
                        "checked_items": 0,
                        "gaps": 0,
                        "critical_gaps": 0,
                        "gap_items": Counter(),
                        "critical_items": Counter(),
                    }
                    for section in self.sections
                },
            }
        )

        for row in rows:
            tank_id = str(row.get("tank_id") or "").strip()
            if not tank_id:
                continue

            has_tank_data = False
            touched_sections: set[str] = set()

            for field_name, value in row.get("fields", {}).items():
                section = self._section_for_field(field_name)
                if not section:
                    continue
                has_tank_data = True
                touched_sections.add(section)

                item_name = self._item_for_field(field_name)
                section_entry = metrics[tank_id]["sections"][section]
                section_entry["checked_items"] += 1
                metrics[tank_id]["checked_items"] += 1

                if self._is_gap(value):
                    section_entry["gaps"] += 1
                    section_entry["gap_items"][item_name] += 1
                    metrics[tank_id]["gaps"] += 1
                    metrics[tank_id]["gap_items"][item_name] += 1
                    if self._is_critical_item(item_name):
                        section_entry["critical_gaps"] += 1
                        section_entry["critical_items"][item_name] += 1
                        metrics[tank_id]["critical_gaps"] += 1
                        metrics[tank_id]["critical_items"][item_name] += 1

            if has_tank_data:
                metrics[tank_id]["reports"] += 1
                for section in touched_sections:
                    metrics[tank_id]["sections"][section]["reports"] += 1

        finalized: dict[str, dict[str, Any]] = {}
        for tank_id, values in metrics.items():
            per_section: dict[str, dict[str, Any]] = {}
            for section in self.sections:
                section_values = values["sections"][section]
                per_section[section] = {
                    "reports": section_values["reports"],
                    "checked_items": section_values["checked_items"],
                    "gaps": section_values["gaps"],
                    "critical_gaps": section_values["critical_gaps"],
                    "readiness_score": self._compute_readiness_score(
                        checked_items=section_values["checked_items"],
                        gaps=section_values["gaps"],
                        critical_gaps=section_values["critical_gaps"],
                    ),
                    "gap_items": [
                        {"item": item, "gaps": count}
                        for item, count in section_values["gap_items"].most_common(10)
                    ],
                    "critical_items": [
                        {"item": item, "gaps": count}
                        for item, count in section_values["critical_items"].most_common(10)
                    ],
                }

            finalized[tank_id] = {
                "reports": values["reports"],
                "checked_items": values["checked_items"],
                "gaps": values["gaps"],
                "critical_gaps": values["critical_gaps"],
                "readiness_score": self._compute_readiness_score(
                    checked_items=values["checked_items"],
                    gaps=values["gaps"],
                    critical_gaps=values["critical_gaps"],
                ),
                "gap_items": [
                    {"item": item, "gaps": count}
                    for item, count in values["gap_items"].most_common(10)
                ],
                "critical_items": [
                    {"item": item, "gaps": count}
                    for item, count in values["critical_items"].most_common(10)
                ],
                "sections": per_section,
            }
        return finalized

    def _aggregate_company_readiness(self, tank_rows: Any) -> dict[str, Any]:
        rows = list(tank_rows)
        readiness_values = [
            row["readiness_score"]
            for row in rows
            if isinstance(row, dict) and row.get("readiness_score") is not None
        ]
        critical_items = Counter()
        critical_tanks = 0
        for row in rows:
            if not isinstance(row, dict):
                continue
            if row.get("critical_gaps", 0) > 0:
                critical_tanks += 1
            for item in row.get("critical_items", []):
                critical_items[item.get("item", "")] += int(item.get("gaps") or 0)
        return {
            "tanks": len(rows),
            "avg_readiness": round(sum(readiness_values) / len(readiness_values), 1) if readiness_values else None,
            "critical_tanks": critical_tanks,
            "critical_items": [
                {"item": item, "gaps": gaps}
                for item, gaps in critical_items.most_common(10)
                if item
            ],
        }

    def _compute_readiness_score(self, checked_items: int, gaps: int, critical_gaps: int = 0) -> Optional[float]:
        if checked_items <= 0:
            return None
        base_score = 100.0 * (1.0 - (float(gaps) / float(checked_items)))
        penalty = min(60.0, float(critical_gaps) * self.critical_gap_penalty)
        return round(max(0.0, base_score - penalty), 1)

    @staticmethod
    def _score_delta(current: Optional[float], previous: Optional[float]) -> Optional[float]:
        if current is None or previous is None:
            return None
        return round(float(current) - float(previous), 1)

    @staticmethod
    def _section_score_value(per_section: dict[str, Any], section: str) -> Optional[float]:
        section_data = per_section.get(section)
        if not isinstance(section_data, dict):
            return None
        score = section_data.get("readiness_score")
        return float(score) if score is not None else None

    @staticmethod
    def _sort_readiness_key(score: Optional[float]) -> float:
        if score is None:
            return -101.0
        try:
            return -float(score)
        except Exception:
            return -101.0

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

    def _canonical_section(self, section: Any) -> Optional[str]:
        if section is None:
            return None
        raw = str(section).strip()
        if not raw:
            return None
        return self._section_lookup.get(raw.lower())

    def _section_for_field(self, field_name: str) -> Optional[str]:
        family = self._family_for_field(field_name)
        mapped = self.family_to_section.get(str(family).strip().lower())
        if mapped:
            return mapped

        item_name = self._item_for_field(field_name).lower()
        if any(token in item_name for token in ["מקמש", "גנטקס", "פתיל", "מדיה", "nfc", "מבן", "תקל"]):
            return self._canonical_section("Communications")
        if any(token in item_name for token in ["שמן", "חלף", "חלפים", "אמצעי", "אמצעים"]):
            return self._canonical_section("Armament")
        if any(token in item_name for token in ["מאג", "תחמושת", "זיווד", "שאקל", "חבל"]):
            return self._canonical_section("Logistics")
        return None

    @staticmethod
    def _normalize_item_name(item_name: str) -> str:
        text = str(item_name or "").strip().lower()
        if not text:
            return ""
        replacements = {
            '"': "",
            "'": "",
            "\\": "",
            "/": "",
            "-": "",
            "_": "",
            ".": "",
            ",": "",
            " ": "",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    def _is_critical_item(self, item_name: str) -> bool:
        key = self._normalize_item_name(item_name)
        if not key:
            return False
        return key in self.critical_item_lookup

    def _previous_week(self, target_week: str, platoon_key: Optional[str] = None) -> Optional[str]:
        if not target_week:
            return None
        weeks = self.list_weeks(platoon_key=platoon_key)
        if not weeks:
            return None
        if target_week in weeks:
            idx = weeks.index(target_week)
            if idx + 1 < len(weeks):
                return weeks[idx + 1]
            return None
        for week in weeks:
            if week < target_week:
                return week
        return None

    def _empty_section_metrics(self, company: str, section: str) -> dict[str, Any]:
        return {
            "company": company,
            "section": section,
            "reports": 0,
            "tanks": 0,
            "checked_items": 0,
            "total_gaps": 0,
            "critical_gaps": 0,
            "gap_rate": 0.0,
            "readiness_score": None,
        }
