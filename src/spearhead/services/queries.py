import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional, Tuple

from spearhead.config import settings
from spearhead.config_fields import field_config
from spearhead.data.storage import Database


class QueryService:
    """
    Deterministic query layer over the persisted imports.
    Focused on gaps/availability for equipment and ammo plus form status analysis.
    """

    def __init__(self, db: Database):
        self.db = db
        gap_source = settings.status_tokens.gap_tokens + field_config.gap_tokens
        ok_source = settings.status_tokens.ok_tokens + field_config.ok_tokens
        self.gap_tokens = tuple(dict.fromkeys(gap_source))
        self.ok_tokens = tuple(dict.fromkeys(ok_source))

    def tabular_totals(
        self,
        section: str,
        top_n: int = 20,
        platoon: Optional[str] = None,
        week: Optional[str] = None,
    ) -> List[Dict]:
        """
        Aggregate numeric totals per item for a given section (e.g., zivud, ammo).
        """
        rows = self._query_totals(section=section, platoon=platoon, week=week, limit=top_n)
        return [{"item": r[0], "total": r[1], "samples": r[2]} for r in rows]

    def tabular_gaps(
        self,
        section: str,
        top_n: int = 20,
        platoon: Optional[str] = None,
        week: Optional[str] = None,
    ) -> List[Dict]:
        """
        Count textual gap tokens (חוסר/בלאי) in tabular records per item.
        """
        counts = Counter()
        with self.db._connect() as conn:
            cur = conn.cursor()
            filters, params = self._build_filters(section=section, platoon=platoon, week=week)
            cur.execute(
                f"""
                SELECT item, value_text FROM tabular_records
                JOIN imports ON tabular_records.import_id = imports.id
                WHERE {" AND ".join(filters)} AND value_text IS NOT NULL
                """,
                params,
            )
            for item, value_text in cur.fetchall():
                text = value_text.strip()
                if any(token in text for token in self.gap_tokens):
                    counts[item] += 1
        return [{"item": item, "gaps": cnt} for item, cnt in counts.most_common(top_n)]

    def form_status_counts(self, top_n: int = 50) -> Dict[str, List[Dict]]:
        """
        Aggregates statuses from form responses.
        Returns two lists: 'gaps' (חוסר/בלאי) and 'ok' (קיים/יש) counts per field.
        """
        gap_counts = Counter()
        ok_counts = Counter()
        with self.db._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT fields_json FROM form_responses")
            for (payload,) in cur.fetchall():
                try:
                    fields = json.loads(payload)
                except Exception:
                    continue
                for key, value in fields.items():
                    if not isinstance(value, str):
                        continue
                    val = value.strip()
                    if any(token in val for token in self.gap_tokens):
                        gap_counts[key] += 1
                    elif any(token in val for token in self.ok_tokens):
                        ok_counts[key] += 1

        return {
            "gaps": [{"field": k, "count": v} for k, v in gap_counts.most_common(top_n)],
            "ok": [{"field": k, "count": v} for k, v in ok_counts.most_common(top_n)],
        }

    def tabular_by_platoon(self, section: str, top_n: int = 20, week: Optional[str] = None) -> List[Dict]:
        """
        Aggregate numeric totals per platoon for a given section.
        """
        results = []
        with self.db._connect() as conn:
            cur = conn.cursor()
            filters, params = self._build_filters(section=section, platoon=None, week=week)
            cur.execute(
                f"""
                SELECT platoon, item, SUM(COALESCE(value_num, 0)) as total_num
                FROM tabular_records
                JOIN imports ON imports.id = tabular_records.import_id
                WHERE {" AND ".join(filters)}
                GROUP BY platoon, item
                ORDER BY platoon, total_num DESC
                """,
                params,
            )
            rows = cur.fetchall()
        platoon_map: Dict[Optional[str], List[Dict]] = defaultdict(list)
        for platoon, item, total_num in rows:
            platoon_map[platoon].append({"item": item, "total": total_num})
        for platoon, items in platoon_map.items():
            results.append({"platoon": platoon, "items": items[:top_n]})
        return results

    def tabular_delta(self, section: str, top_n: int = 20) -> List[Dict]:
        """
        Delta between the latest two imports for a given section.
        Returns item, current, previous, delta, direction, pct_change.
        """
        import_ids = self._latest_imports_for_section(section, 2)
        if len(import_ids) < 2:
            return []
        current_id, prev_id = import_ids[0], import_ids[1]

        current_totals = self._totals_for_import(section, current_id)
        prev_totals = self._totals_for_import(section, prev_id)

        items = set(current_totals) | set(prev_totals)
        deltas = []
        for item in items:
            cur = current_totals.get(item, 0.0)
            prev = prev_totals.get(item, 0.0)
            delta = cur - prev
            direction = "up" if delta > 0 else "down" if delta < 0 else "flat"
            pct_change = None
            if prev not in (0, None):
                try:
                    pct_change = (delta / prev) * 100
                except Exception:
                    pct_change = None
            deltas.append(
                {
                    "item": item,
                    "current": cur,
                    "previous": prev,
                    "delta": delta,
                    "direction": direction,
                    "pct_change": pct_change,
                }
            )

        deltas.sort(key=lambda x: abs(x["delta"]), reverse=True)
        return deltas[:top_n]

    def tabular_variance_vs_summary(self, section: str, top_n: int = 20) -> List[Dict]:
        """
        Compare latest platoon section totals to latest battalion summary totals.
        """
        summary_map = {"zivud": "summary_zivud", "ammo": "summary_ammo"}
        summary_section = summary_map.get(section)
        if not summary_section:
            return []

        import_ids_section = self._latest_imports_for_section(section, 1)
        import_ids_summary = self._latest_imports_for_section(summary_section, 1)
        if not import_ids_section or not import_ids_summary:
            return []

        cur_totals = self._totals_for_import(section, import_ids_section[0])
        sum_totals = self._totals_for_import(summary_section, import_ids_summary[0])

        items = set(cur_totals) | set(sum_totals)
        diffs = []
        for item in items:
            cur = cur_totals.get(item, 0.0)
            summary_val = sum_totals.get(item, 0.0)
            diff = cur - summary_val
            direction = "up" if diff > 0 else "down" if diff < 0 else "flat"
            pct_change = None
            if summary_val not in (0, None):
                try:
                    pct_change = (diff / summary_val) * 100
                except Exception:
                    pct_change = None
            diffs.append(
                {
                    "item": item,
                    "current": cur,
                    "summary": summary_val,
                    "variance": diff,
                    "direction": direction,
                    "pct_change": pct_change,
                }
            )

        diffs.sort(key=lambda x: abs(x["variance"]), reverse=True)
        return diffs[:top_n]

    def tabular_trends(
        self,
        section: str,
        top_n: int = 5,
        platoon: Optional[str] = None,
        window_weeks: int = 8,
    ) -> List[Dict]:
        """
        Trendlines for top items over recent weeks (ISO week).
        Returns list of {item, points:[{week,total}]} ordered by total desc.
        """
        recent_cutoff = datetime.now(UTC) - timedelta(weeks=window_weeks)
        week_expr = "strftime('%Y-W%W', datetime(imports.created_at))"

        filters, params = self._build_filters(section=section, platoon=platoon, week=None)
        filters.append("datetime(imports.created_at) >= ?")
        params.append(recent_cutoff.isoformat())

        with self.db._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                f"""
                SELECT tabular_records.item, SUM(COALESCE(tabular_records.value_num, 0)) as total_num
                FROM tabular_records
                JOIN imports ON imports.id = tabular_records.import_id
                WHERE {" AND ".join(filters)}
                GROUP BY tabular_records.item
                ORDER BY total_num DESC
                LIMIT ?
                """,
                (*params, top_n),
            )
            top_items = [row[0] for row in cur.fetchall()]

        if not top_items:
            return []

        placeholders = ",".join(["?"] * len(top_items))
        with self.db._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                f"""
                SELECT tabular_records.item, {week_expr} as week_label, SUM(COALESCE(tabular_records.value_num, 0)) as total_num
                FROM tabular_records
                JOIN imports ON imports.id = tabular_records.import_id
                WHERE {" AND ".join(filters)} AND tabular_records.item IN ({placeholders})
                GROUP BY tabular_records.item, week_label
                ORDER BY week_label ASC
                """,
                (*params, *top_items),
            )
            rows = cur.fetchall()

        series: Dict[str, List[Dict]] = {item: [] for item in top_items}
        for item, week_label, total_num in rows:
            series[item].append({"week": week_label, "total": total_num})

        return [{"item": item, "points": series[item]} for item in top_items]

    def _latest_imports_for_section(self, section: str, limit: int) -> List[int]:
        with self.db._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT imports.id
                FROM imports
                JOIN tabular_records ON tabular_records.import_id = imports.id
                WHERE tabular_records.section = ?
                GROUP BY imports.id
                ORDER BY imports.created_at DESC
                LIMIT ?
                """,
                (section, limit),
            )
            rows = cur.fetchall()
        return [row[0] for row in rows]

    def _totals_for_import(self, section: str, import_id: int) -> Dict[str, float]:
        with self.db._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT item, SUM(COALESCE(value_num, 0)) as total_num
                FROM tabular_records
                WHERE section = ? AND import_id = ?
                GROUP BY item
                """,
                (section, import_id),
            )
            rows = cur.fetchall()
        return {item: total for item, total in rows}

    @staticmethod
    def _week_label_from_datetime(dt: datetime) -> str:
        return dt.strftime("%Y-W%W")

    def _build_filters(self, section: str, platoon: Optional[str], week: Optional[str]) -> Tuple[List[str], List]:
        filters = ["tabular_records.section = ?"]
        params: List = [section]
        if platoon:
            filters.append("tabular_records.platoon = ?")
            params.append(platoon)
        if week:
            filters.append("strftime('%Y-W%W', datetime(imports.created_at)) = ?")
            params.append(week)
        return filters, params

    def _query_totals(
        self, section: str, platoon: Optional[str], week: Optional[str], limit: int
    ) -> List[tuple]:
        filters, params = self._build_filters(section=section, platoon=platoon, week=week)
        with self.db._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                f"""
                SELECT tabular_records.item,
                    SUM(COALESCE(tabular_records.value_num, 0)) as total_num,
                    COUNT(*) as samples
                FROM tabular_records
                JOIN imports ON imports.id = tabular_records.import_id
                WHERE {" AND ".join(filters)}
                GROUP BY tabular_records.item
                ORDER BY total_num DESC
                LIMIT ?
                """,
                (*params, limit),
            )
            return cur.fetchall()
