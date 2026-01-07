import json
from collections import Counter, defaultdict
from typing import Dict, List, Optional

from iron_view.data.storage import Database


class QueryService:
    """
    Deterministic query layer over the persisted imports.
    Focused on gaps/availability for equipment and ammo plus form status analysis.
    """

    GAP_TOKENS = ("חוסר", "בלאי")
    OK_TOKENS = ("קיים", "יש")

    def __init__(self, db: Database):
        self.db = db

    def tabular_totals(self, section: str, top_n: int = 20) -> List[Dict]:
        """
        Aggregate numeric totals per item for a given section (e.g., zivud, ammo).
        """
        with self.db._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT item, SUM(COALESCE(value_num, 0)) as total_num, COUNT(*) as samples
                FROM tabular_records
                WHERE section = ?
                GROUP BY item
                ORDER BY total_num DESC
                LIMIT ?
                """,
                (section, top_n),
            )
            rows = cur.fetchall()
        return [{"item": r[0], "total": r[1], "samples": r[2]} for r in rows]

    def tabular_gaps(self, section: str, top_n: int = 20) -> List[Dict]:
        """
        Count textual gap tokens (חוסר/בלאי) in tabular records per item.
        """
        counts = Counter()
        with self.db._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT item, value_text FROM tabular_records
                WHERE section = ? AND value_text IS NOT NULL
                """,
                (section,),
            )
            for item, value_text in cur.fetchall():
                text = value_text.strip()
                if any(token in text for token in self.GAP_TOKENS):
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
                    if any(token in val for token in self.GAP_TOKENS):
                        gap_counts[key] += 1
                    elif any(token in val for token in self.OK_TOKENS):
                        ok_counts[key] += 1

        return {
            "gaps": [{"field": k, "count": v} for k, v in gap_counts.most_common(top_n)],
            "ok": [{"field": k, "count": v} for k, v in ok_counts.most_common(top_n)],
        }

    def tabular_by_platoon(self, section: str, top_n: int = 20) -> List[Dict]:
        """
        Aggregate numeric totals per platoon for a given section.
        """
        results = []
        with self.db._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT platoon, item, SUM(COALESCE(value_num, 0)) as total_num
                FROM tabular_records
                WHERE section = ?
                GROUP BY platoon, item
                ORDER BY platoon, total_num DESC
                """,
                (section,),
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
        Returns item, current, previous, delta.
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
            deltas.append({"item": item, "current": cur, "previous": prev, "delta": delta})

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
            diffs.append({"item": item, "current": cur, "summary": summary_val, "variance": diff})

        diffs.sort(key=lambda x: abs(x["variance"]), reverse=True)
        return diffs[:top_n]

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
