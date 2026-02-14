from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any, Optional
from zoneinfo import ZoneInfo

from spearhead.config import settings
from spearhead.config_fields import field_config
from spearhead.data.field_mapper import FieldMapper
from spearhead.ai import build_ai_client
from spearhead.operational_standards import load_operational_standards
from spearhead.v1.models import (
    CompanyAssetEventV2,
    CompanyAssetIngestionReportV2,
    FormEventV2,
    IngestionReportV2,
    MetricSnapshotV2,
    NormalizedResponseV2,
)
from spearhead.v1.parser import CompanyAssetParserV2, EventValidationError, FormResponseParserV2
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


class CompanyAssetIngestionServiceV2:
    def __init__(self, store: ResponseStore, parser: CompanyAssetParserV2):
        self.store = store
        self.parser = parser

    def ingest_event(self, event: CompanyAssetEventV2) -> CompanyAssetIngestionReportV2:
        payload_hash = hashlib.sha256(
            json.dumps(event.payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        event_id = event.event_id or hashlib.sha256(
            f"company-assets|{event.schema_version}|{event.source_id}|{payload_hash}".encode("utf-8")
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
            existing = self.store.list_company_assets()
            week_id = None
            company_key = None
            for item in existing:
                if item["event_id"] == event_id:
                    week_id = item["week_id"]
                    company_key = item["company_key"]
                    break
            return CompanyAssetIngestionReportV2(
                event_id=event_id,
                created=False,
                schema_version=event.schema_version,
                source_id=event.source_id,
                week_id=week_id,
                company_key=company_key,
            )

        try:
            normalized = self.parser.parse(event)
            self.store.upsert_company_asset(normalized)
            self.store.mark_event_status(event_id, status="processed")
            return CompanyAssetIngestionReportV2(
                event_id=event_id,
                created=True,
                schema_version=event.schema_version,
                source_id=event.source_id,
                week_id=normalized.week_id,
                company_key=normalized.company_key,
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
    _WEEK_ID_PATTERN = re.compile(r"^(?P<year>\d{4})-W(?P<week>\d{2})$")
    _DEFAULT_WEEK_TIMEZONE = "Asia/Jerusalem"

    def __init__(self, store: ResponseStore):
        self.store = store
        self.standards = load_operational_standards(settings.operational.standards_path)
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
        configured_companies = (
            self.standards.active_companies
            or settings.operational.enabled_companies
            or settings.operational.company_order
            or ["Kfir", "Mahatz", "Sufa"]
        )
        company_order: list[str] = []
        for company in configured_companies:
            canonical = self._canonical_company(company)
            if not canonical or canonical == "Battalion":
                continue
            if canonical not in company_order:
                company_order.append(canonical)
        self.company_order = company_order
        self._company_rank = {
            company.lower(): index
            for index, company in enumerate(self.company_order)
        }

        critical_items = self.standards.critical_items or settings.operational.critical_item_names or []
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

    def week_metadata(self, platoon_key: Optional[str] = None) -> dict[str, Any]:
        weeks = self.list_weeks(platoon_key=platoon_key)
        timezone_name = self._DEFAULT_WEEK_TIMEZONE
        today = datetime.now(ZoneInfo(timezone_name)).date()

        options: list[dict[str, Any]] = []
        current_week: Optional[str] = None

        for week_id in weeks:
            option = self._build_week_option(week_id=week_id, today=today)
            if option["is_current"] and current_week is None:
                current_week = week_id
            options.append(option)

        return {
            "weeks": weeks,
            "current_week": current_week,
            "week_options": options,
            "timezone": timezone_name,
            "week_starts_on": "sunday",
        }

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

        metric_companies = {
            self._canonical_company(company)
            for company, _ in current_metrics.keys() | previous_metrics.keys()
        }
        metric_companies = {company for company in metric_companies if company and company != "Battalion"}
        if platoon_scope:
            companies = [self._canonical_company(platoon_scope)]
        else:
            companies = list(self.company_order)
            for company in sorted(metric_companies, key=self._company_sort_key):
                if company not in companies:
                    companies.append(company)

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

        trends = self._build_battalion_company_trends(
            target_week=target_week,
            platoon_scope=platoon_scope,
            companies=companies,
            window_weeks=8,
        )

        return {
            "week_id": target_week,
            "previous_week_id": previous_week,
            "scope": platoon_scope,
            "sections": list(self.sections),
            "section_display_names": self.section_display_names,
            "section_scope_notes": self.section_scope_notes,
            "companies": companies,
            "trends": trends,
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
        all_rows = self.store.list_normalized(platoon_key=company)

        current_metrics = self._compute_tank_overall_metrics(current_rows)
        previous_metrics = self._compute_tank_overall_metrics(previous_rows)
        summary = self._aggregate_company_readiness(current_metrics.values())
        known_tank_ids = sorted(
            {
                str(row.get("tank_id") or "").strip()
                for row in all_rows
                if str(row.get("tank_id") or "").strip()
            }
        )
        if not known_tank_ids:
            known_tank_ids = sorted(current_metrics.keys())

        reported_tanks = sum(
            1 for tank_id in known_tank_ids if int(current_metrics.get(tank_id, {}).get("reports") or 0) > 0
        )
        summary["known_tanks"] = len(known_tank_ids)
        summary["reported_tanks"] = reported_tanks
        summary["missing_reports"] = max(len(known_tank_ids) - reported_tanks, 0)

        rows: list[dict[str, Any]] = []
        for tank_id in known_tank_ids:
            current = current_metrics.get(tank_id, {})
            previous = previous_metrics.get(tank_id, {})
            current_reports = int(current.get("reports") or 0)
            reported_this_week = current_reports > 0
            current_gaps = int(current.get("gaps") or 0)
            current_critical = int(current.get("critical_gaps") or 0)
            per_section = current.get("sections", {})
            previous_gaps = int(previous.get("gaps") or 0)
            rows.append(
                {
                    "tank_id": tank_id,
                    "status": "NoReport"
                    if not reported_this_week
                    else ("Critical" if current_critical > 0 else ("Gap" if current_gaps > 0 else "OK")),
                    "reported_this_week": reported_this_week,
                    "reports": current_reports,
                    "checked_items": int(current.get("checked_items") or 0),
                    "gaps": current_gaps,
                    "critical_gaps": current_critical,
                    "critical_items": current.get("critical_items", []),
                    "readiness_score": current.get("readiness_score"),
                    "delta_readiness": None
                    if not reported_this_week
                    else self._score_delta(
                        current.get("readiness_score"),
                        previous.get("readiness_score"),
                    ),
                    "delta_gaps": None if not reported_this_week else current_gaps - previous_gaps,
                    "sections": per_section,
                    "logistics_readiness": self._section_score_value(per_section, "Logistics"),
                    "armament_readiness": self._section_score_value(per_section, "Armament"),
                    "communications_readiness": self._section_score_value(per_section, "Communications"),
                }
            )

        rows.sort(
            key=lambda row: (
                row.get("reported_this_week", False),
                row.get("critical_gaps", 0),
                self._sort_readiness_key(row.get("readiness_score")),
                row.get("gaps", 0),
                row.get("tank_id", ""),
            ),
            reverse=True,
        )

        critical_gaps_table = self._build_critical_gaps_table(rows)
        ammo_averages = self._compute_ammo_averages(current_rows=current_rows)
        trends = self._build_company_trends(company=company, target_week=target_week, window_weeks=6)

        return {
            "week_id": target_week,
            "previous_week_id": previous_week,
            "company": company,
            "section_display_names": self.section_display_names,
            "section_scope_notes": self.section_scope_notes,
            "summary": summary,
            "critical_gaps_table": critical_gaps_table,
            "ammo_averages": ammo_averages,
            "trends": trends,
            "rows": rows,
        }

    def company_tank_inventory_view(self, company_key: str, tank_id: str, week_id: Optional[str]) -> dict[str, Any]:
        target_week = week_id or self.latest_week()
        company = self._canonical_company(company_key)
        normalized_tank = self._normalize_tank_id(tank_id)
        if not target_week:
            return {
                "week_id": None,
                "company": company,
                "tank_id": normalized_tank or tank_id,
                "rows": [],
            }

        rows = self.store.list_normalized(week_id=target_week, platoon_key=company)
        tank_rows = [
            row for row in rows
            if self._normalize_tank_id(row.get("tank_id")) == normalized_tank
        ]
        if not tank_rows:
            return {
                "week_id": target_week,
                "company": company,
                "tank_id": normalized_tank or tank_id,
                "rows": [],
            }

        # Merge item status across submissions during the same week.
        # Latest report wins for each field.
        merged_fields: dict[str, Any] = {}
        for row in sorted(tank_rows, key=lambda item: str(item.get("received_at") or "")):
            for field_name, value in row.get("fields", {}).items():
                merged_fields[field_name] = value

        result_rows: list[dict[str, Any]] = []
        for field_name, value in merged_fields.items():
            section = self._section_for_field(field_name) or "Unclassified"
            family = self._family_for_field(field_name)
            item = self._item_for_field(field_name)
            result_rows.append(
                {
                    "field_name": field_name,
                    "item": item,
                    "section": section,
                    "family": family,
                    "status": self._normalize_inventory_status(value),
                    "is_gap": self._is_gap(value),
                    "is_critical": self._is_critical_item(item),
                    "raw_value": value,
                    "has_category_code": self._has_category_code(item),
                    "standard_quantity": self.standards.tank_standard_for_item(item),
                }
            )

        result_rows.sort(
            key=lambda row: (
                self._section_sort_key(row.get("section")),
                row.get("item", ""),
            )
        )
        return {
            "week_id": target_week,
            "company": company,
            "tank_id": normalized_tank or tank_id,
            "rows": result_rows,
        }

    def company_assets_view(self, company_key: str, week_id: Optional[str]) -> dict[str, Any]:
        target_week = week_id or self.latest_week()
        company = self._canonical_company(company_key)
        if not target_week:
            return {
                "week_id": None,
                "company": company,
                "rows": [],
                "summary": {"items": 0, "gaps": 0, "critical": 0},
            }

        events = self.store.list_company_assets(week_id=target_week, company_key=company)
        if not events:
            return {
                "week_id": target_week,
                "company": company,
                "rows": [],
                "summary": {"items": 0, "gaps": 0, "critical": 0},
            }

        latest_fields: dict[str, Any] = {}
        for event in sorted(events, key=lambda item: str(item.get("received_at") or "")):
            latest_fields.update(event.get("fields", {}))

        table: list[dict[str, Any]] = []
        for field_name, value in latest_fields.items():
            item = self._item_for_field(field_name)
            bucket = self._classify_company_asset(item=item, field_name=field_name)
            is_gap = self._is_gap(value)
            detected_category_code = self._has_category_code(item) or self._has_category_code(str(value))
            table.append(
                {
                    "field_name": field_name,
                    "item": item,
                    "section": bucket["section"],
                    "group": bucket["group"],
                    "status": self._normalize_inventory_status(value),
                    "is_gap": is_gap,
                    "is_critical": bucket["is_critical"],
                    "raw_value": value,
                    "has_category_code": detected_category_code,
                    "requires_category_code": bool(bucket.get("requires_category_code", False)),
                    "standard_quantity": bucket.get("standard_quantity"),
                }
            )

        table.sort(key=lambda row: (row.get("section", ""), row.get("group", ""), row.get("item", "")))
        summary = {
            "items": len(table),
            "gaps": sum(1 for row in table if row.get("is_gap")),
            "critical": sum(1 for row in table if row.get("is_critical") and row.get("is_gap")),
        }
        return {
            "week_id": target_week,
            "company": company,
            "rows": table,
            "summary": summary,
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
            platoon = self._canonical_company(row.get("platoon_key") or "Unknown")
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
        companies = sorted(
            {self._canonical_company(row.get("platoon_key") or "Unknown") for row in rows},
            key=self._company_sort_key,
        )
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
            company = self._canonical_company(row.get("platoon_key") or "Unknown")
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

    @staticmethod
    def _build_critical_gaps_table(tank_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        per_item: dict[str, dict[str, Any]] = {}
        for row in tank_rows:
            tank_id = str(row.get("tank_id") or "").strip()
            critical_items = row.get("critical_items", [])
            if not isinstance(critical_items, list):
                continue
            for critical in critical_items:
                if not isinstance(critical, dict):
                    continue
                item_name = str(critical.get("item") or "").strip()
                if not item_name:
                    continue
                gaps = int(critical.get("gaps") or 0)
                entry = per_item.setdefault(
                    item_name,
                    {
                        "item": item_name,
                        "gaps": 0,
                        "tanks_set": set(),
                    },
                )
                entry["gaps"] += gaps
                if tank_id:
                    entry["tanks_set"].add(tank_id)

        result = []
        for values in per_item.values():
            tanks = sorted(values["tanks_set"])
            result.append(
                {
                    "item": values["item"],
                    "gaps": values["gaps"],
                    "tanks": tanks,
                    "tanks_count": len(tanks),
                }
            )
        result.sort(key=lambda row: (row.get("gaps", 0), row.get("item", "")), reverse=True)
        return result

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

    def _normalize_inventory_status(self, value: Any) -> str:
        if value is None:
            return "-"
        text = str(value).strip()
        if not text:
            return "-"
        lower = text.lower()
        if "חוסר" in lower or "חסר" in lower or "אין" in lower:
            return "חוסר"
        if "בלאי" in lower or "תקול" in lower:
            return "תקול/בלאי"
        if "קיים" in lower or "יש" in lower or "תקין" in lower:
            return "תקין"
        return text

    def _compute_ammo_averages(self, current_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        per_item: dict[str, dict[str, Any]] = {}
        tank_items_seen: set[tuple[str, str]] = set()
        tank_ids = {
            self._normalize_tank_id(row.get("tank_id"))
            for row in current_rows
            if self._normalize_tank_id(row.get("tank_id"))
        }
        for row in current_rows:
            tank_id = self._normalize_tank_id(row.get("tank_id"))
            if not tank_id:
                continue
            for field_name, value in row.get("fields", {}).items():
                family = self._family_for_field(field_name)
                section = self._section_for_field(field_name)
                if family != "ammo" and section != "Logistics":
                    continue
                item = self._item_for_field(field_name)
                key = (tank_id, item)
                if key in tank_items_seen:
                    continue
                tank_items_seen.add(key)
                bucket = per_item.setdefault(
                    item,
                    {
                        "item": item,
                        "tanks_total": len(tank_ids),
                        "available_tanks": 0,
                        "gap_tanks": 0,
                    },
                )
                if self._is_gap(value):
                    bucket["gap_tanks"] += 1
                else:
                    bucket["available_tanks"] += 1

        result: list[dict[str, Any]] = []
        for item, values in per_item.items():
            total = int(values.get("tanks_total") or 0)
            available = int(values.get("available_tanks") or 0)
            rate = round((available / total) * 100.0, 1) if total else 0.0
            result.append(
                {
                    "item": item,
                    "available_tanks": available,
                    "gap_tanks": int(values.get("gap_tanks") or 0),
                    "total_tanks": total,
                    "coverage_rate": rate,
                    "availability_rate": rate,
                }
            )
        result.sort(key=lambda row: (row.get("availability_rate", 0.0), row.get("item", "")))
        return result[:30]

    def _build_company_trends(self, company: str, target_week: str, window_weeks: int = 6) -> dict[str, Any]:
        weeks = self.list_weeks(platoon_key=company)
        if not weeks:
            return {"readiness": [], "critical_gaps": [], "tank_readiness": [], "tank_series": []}
        if target_week in weeks:
            start_idx = weeks.index(target_week)
            scope_weeks = list(reversed(weeks[start_idx : start_idx + max(window_weeks, 1)]))
        else:
            scope_weeks = list(reversed(weeks[: max(window_weeks, 1)]))

        readiness_rows: list[dict[str, Any]] = []
        critical_rows: list[dict[str, Any]] = []
        tank_rows: list[dict[str, Any]] = []
        tank_keys_seen: set[str] = set()
        for week_id in scope_weeks:
            week_rows = self.store.list_normalized(week_id=week_id, platoon_key=company)
            tank_metrics = self._compute_tank_overall_metrics(week_rows)
            summary = self._aggregate_company_readiness(tank_metrics.values())
            readiness_rows.append(
                {
                    "week_id": week_id,
                    "value": summary.get("avg_readiness"),
                }
            )
            critical_rows.append(
                {
                    "week_id": week_id,
                    "value": sum(int(row.get("critical_gaps") or 0) for row in tank_metrics.values()),
                }
            )
            tank_row: dict[str, Any] = {"week_id": week_id}
            for tank_id, tank_values in tank_metrics.items():
                normalized = self._normalize_tank_id(tank_id)
                if not normalized:
                    continue
                key = f"tank_{normalized}"
                tank_keys_seen.add(key)
                tank_row[key] = tank_values.get("readiness_score")
            tank_rows.append(tank_row)

        tank_keys = sorted(
            tank_keys_seen,
            key=lambda key: key.replace("tank_", ""),
        )
        for row in tank_rows:
            for key in tank_keys:
                row.setdefault(key, None)

        tank_series = [
            {
                "key": key,
                "tank_id": key.replace("tank_", ""),
            }
            for key in tank_keys
        ]

        return {
            "readiness": readiness_rows,
            "critical_gaps": critical_rows,
            "tank_readiness": tank_rows,
            "tank_series": tank_series,
        }

    def _build_battalion_company_trends(
        self,
        *,
        target_week: str,
        platoon_scope: Optional[str],
        companies: list[str],
        window_weeks: int = 8,
    ) -> dict[str, Any]:
        if platoon_scope:
            weeks = self.list_weeks(platoon_key=platoon_scope)
        else:
            weeks = self.list_weeks()
        if not weeks:
            return {"readiness_by_company": [], "companies": companies}

        if target_week in weeks:
            start_idx = weeks.index(target_week)
            scope_weeks = list(reversed(weeks[start_idx : start_idx + max(window_weeks, 1)]))
        else:
            scope_weeks = list(reversed(weeks[: max(window_weeks, 1)]))

        readiness_rows: list[dict[str, Any]] = []
        for week_id in scope_weeks:
            row = {"week_id": week_id}
            for company in companies:
                week_rows = self.store.list_normalized(week_id=week_id, platoon_key=company)
                tank_metrics = self._compute_tank_overall_metrics(week_rows)
                summary = self._aggregate_company_readiness(tank_metrics.values())
                row[company] = summary.get("avg_readiness")
            readiness_rows.append(row)

        return {
            "readiness_by_company": readiness_rows,
            "companies": companies,
        }

    def battalion_ai_analysis_view(self, week_id: Optional[str], platoon_scope: Optional[str] = None) -> dict[str, Any]:
        payload = self.battalion_sections_view(week_id=week_id, platoon_scope=platoon_scope)
        rows = payload.get("rows", [])
        if not rows:
            return {
                "week_id": payload.get("week_id"),
                "scope": platoon_scope,
                "content": "אין מספיק נתונים לניתוח.",
                "source": "deterministic",
            }

        sorted_critical = sorted(
            rows,
            key=lambda row: int(row.get("critical_gaps") or 0),
            reverse=True,
        )[:5]
        sorted_readiness = sorted(
            rows,
            key=lambda row: float(row.get("readiness_score") or 0.0),
            reverse=True,
        )[:5]
        context = json.dumps(
            {
                "week_id": payload.get("week_id"),
                "previous_week_id": payload.get("previous_week_id"),
                "scope": platoon_scope,
                "top_critical": sorted_critical,
                "top_readiness": sorted_readiness,
                "trends": payload.get("trends", {}),
            },
            ensure_ascii=False,
        )[:7000]
        prompt = (
            "נתח בקצרה את מצב הגדוד בעברית עבור מפקד: "
            "תן תמונת מצב, 3 סיכונים מיידיים, ו-3 פעולות מומלצות לשבוע הקרוב."
        )
        if not settings.ai.enabled or settings.ai.provider == "offline":
            content = self._deterministic_battalion_summary(rows)
            source = "deterministic"
        else:
            try:
                ai_client = build_ai_client(settings)
                result = ai_client.generate(prompt=prompt, context=context)
                content = result.content
                source = result.source
            except Exception:
                content = self._deterministic_battalion_summary(rows)
                source = "deterministic"

        return {
            "week_id": payload.get("week_id"),
            "scope": platoon_scope,
            "content": content,
            "source": source,
        }

    @staticmethod
    def _deterministic_battalion_summary(rows: list[dict[str, Any]]) -> str:
        ranked_critical = sorted(rows, key=lambda row: int(row.get("critical_gaps") or 0), reverse=True)
        ranked_readiness = sorted(rows, key=lambda row: float(row.get("readiness_score") or 0.0), reverse=True)
        top_critical = ranked_critical[0] if ranked_critical else None
        top_readiness = ranked_readiness[0] if ranked_readiness else None
        critical_text = (
            f"{top_critical.get('company')} / {top_critical.get('section')} ({top_critical.get('critical_gaps', 0)})"
            if top_critical
            else "אין"
        )
        readiness_text = (
            f"{top_readiness.get('company')} / {top_readiness.get('section')} ({top_readiness.get('readiness_score')})"
            if top_readiness
            else "אין"
        )
        return (
            "סיכום אוטומטי דטרמיניסטי: "
            f"כיס הקריטי המרכזי: {critical_text}. "
            f"החתך החזק ביותר: {readiness_text}. "
            "המלצות: לתעדף טיפול בפריטים הקריטיים, לסגור פערי דיווח, ולעקוב אחרי מגמת כשירות שבועית."
        )

    @staticmethod
    def _normalize_tank_id(tank_id: Any) -> str:
        raw = str(tank_id or "").strip()
        if not raw:
            return ""
        match = re.search(r"\d{2,4}", raw)
        if not match:
            return raw
        return match.group(0)

    @staticmethod
    def _has_category_code(value: Any) -> bool:
        text = str(value or "").strip()
        if not text:
            return False
        if re.search(r"צ[׳']?\s*\d{2,6}", text):
            return True
        return bool(re.search(r"\b\d{5,7}\b", text))

    def _section_sort_key(self, section: Any) -> tuple[int, str]:
        raw = str(section or "").strip()
        for index, known in enumerate(self.sections):
            if raw.lower() == known.lower():
                return index, raw
        return len(self.sections), raw

    def _classify_company_asset(self, *, item: str, field_name: str) -> dict[str, Any]:
        standard_item = self.standards.find_company_asset(item_name=item, field_name=field_name)
        if standard_item:
            return {
                "section": standard_item.section,
                "group": standard_item.group,
                "is_critical": standard_item.is_critical,
                "requires_category_code": standard_item.has_category_code,
                "standard_quantity": standard_item.standard_quantity,
            }

        token = f"{item} {field_name}".lower()
        if 'ח"ח' in token or "חלפ" in token:
            return {
                "section": "Armament",
                "group": "חלפים",
                "is_critical": True,
                "requires_category_code": False,
                "standard_quantity": None,
            }
        if any(mark in token for mark in ("2510", "2640", "גריז", "שמן")):
            return {
                "section": "Armament",
                "group": "שמנים",
                "is_critical": False,
                "requires_category_code": False,
                "standard_quantity": None,
            }
        if "צלם" in token:
            return {
                "section": "Company Assets",
                "group": "דוח צלם",
                "is_critical": False,
                "requires_category_code": False,
                "standard_quantity": None,
            }
        if "ת\"ת" in token or "ת״ת" in token:
            return {
                "section": "Company Assets",
                "group": "דוח ת\"ת",
                "is_critical": False,
                "requires_category_code": False,
                "standard_quantity": None,
            }
        if "רנגלר" in token or "קשפל" in token:
            return {
                "section": "Company Assets",
                "group": "ציוד פלוגתי",
                "is_critical": False,
                "requires_category_code": False,
                "standard_quantity": None,
            }
        return {
            "section": "Company Assets",
            "group": "כללי",
            "is_critical": False,
            "requires_category_code": False,
            "standard_quantity": None,
        }

    @staticmethod
    def _canonical_company(company: Any) -> str:
        raw = str(company or "").strip()
        if not raw:
            return "Unknown"
        token = (
            raw.replace("׳", "")
            .replace("״", "")
            .replace("'", "")
            .replace('"', "")
            .replace(" ", "")
            .lower()
        )
        aliases = {
            "כפיר": "Kfir",
            "kfir": "Kfir",
            "kphir": "Kfir",
            "מחץ": "Mahatz",
            "mahatz": "Mahatz",
            "machatz": "Mahatz",
            "סופה": "Sufa",
            "sufa": "Sufa",
            "פלסמ": "Palsam",
            "פלסם": "Palsam",
            "palsam": "Palsam",
            "גדוד": "Battalion",
            "battalion": "Battalion",
        }
        return aliases.get(token, raw)

    def _company_sort_key(self, company: str) -> tuple[int, str]:
        canonical = self._canonical_company(company)
        rank = self._company_rank.get(canonical.lower(), len(self._company_rank))
        return rank, canonical.lower()

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

    def _build_week_option(self, week_id: str, *, today: date) -> dict[str, Any]:
        parsed = self._parse_week_id(week_id)
        if not parsed:
            return {
                "value": week_id,
                "label": week_id,
                "week_number": None,
                "start_date": None,
                "end_date": None,
                "is_current": False,
            }

        year, week_num = parsed
        try:
            monday = datetime.fromisocalendar(year, week_num, 1).date()
        except ValueError:
            return {
                "value": week_id,
                "label": week_id,
                "week_number": week_num,
                "start_date": None,
                "end_date": None,
                "is_current": False,
            }

        # UI week starts on Sunday (Israel), while stored week_id remains ISO-based.
        week_start = monday - timedelta(days=1)
        week_end = week_start + timedelta(days=6)
        is_current = week_start <= today <= week_end
        label = f"שבוע {week_num} · {week_start.strftime('%d.%m.%Y')} - {week_end.strftime('%d.%m.%Y')}"

        return {
            "value": week_id,
            "label": label,
            "week_number": week_num,
            "start_date": week_start.isoformat(),
            "end_date": week_end.isoformat(),
            "is_current": is_current,
        }

    @classmethod
    def _parse_week_id(cls, week_id: str) -> Optional[tuple[int, int]]:
        if not week_id:
            return None
        match = cls._WEEK_ID_PATTERN.match(str(week_id).strip())
        if not match:
            return None
        year = int(match.group("year"))
        week = int(match.group("week"))
        return year, week

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
