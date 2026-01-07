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
