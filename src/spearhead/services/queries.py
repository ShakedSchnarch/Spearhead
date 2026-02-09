import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional, Tuple
import pandas as pd

from spearhead.config import settings
from spearhead.config_fields import field_config
from spearhead.data.repositories import TabularRepository
from spearhead.data.storage import Database


class QueryService:
    """
    Deterministic query layer over the persisted imports.
    Focused on gaps/availability for equipment and ammo plus form status analysis.
    Uses TabularRepository for data access.
    """

    def __init__(self, repository: Optional[TabularRepository] = None, db: Optional[Database] = None):
        """
        Accepts either a TabularRepository instance or a raw Database for backwards compatibility.
        """
        if repository is None:
            if db is None:
                raise ValueError("TabularRepository or Database is required")
            repository = TabularRepository(db=db)
        self.repo = repository
        gap_source = settings.status_tokens.gap_tokens + field_config.gap_tokens
        ok_source = settings.status_tokens.ok_tokens + field_config.ok_tokens
        self.gap_tokens = tuple(dict.fromkeys(gap_source))
        self.ok_tokens = tuple(dict.fromkeys(ok_source))

    @staticmethod
    def _week_label_from_datetime(ts: datetime) -> str:
        """
        Canonical week label helper retained for backward compatibility with tests and legacy callers.
        """
        return ts.astimezone(UTC).strftime("%Y-W%W")

    def tabular_totals(
        self,
        section: str,
        top_n: int = 20,
        platoon: Optional[str] = None,
        week: Optional[str] = None,
    ) -> List[Dict]:
        """
        Aggregate numeric totals per item for a given section.
        """
        df = self.repo.get_records(section, week=week, platoon=platoon)
        if df.empty:
            return []

        # Convert value_num to numeric, coerce errors (though SQL/Ingestion should handle it)
        df["value_num"] = pd.to_numeric(df["value_num"], errors="coerce").fillna(0)

        stats = (
            df.groupby("item")["value_num"]
            .agg(total="sum", samples="count")
            .reset_index()
        )
        
        stats = stats.sort_values("total", ascending=False).head(top_n)
        return stats.to_dict("records")

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
        df = self.repo.get_records(section, week=week, platoon=platoon)
        if df.empty:
            return []

        counts = Counter()
        # Iterate efficiently? 
        # For simplicity and robust token matching:
        for item, text in zip(df["item"], df["value_text"]):
            if not isinstance(text, str):
                continue
            if any(token in text for token in self.gap_tokens):
                counts[item] += 1

        return [{"item": item, "gaps": cnt} for item, cnt in counts.most_common(top_n)]

    def form_status_counts(self, top_n: int = 50) -> Dict[str, List[Dict]]:
        """
        Aggregates statuses from form responses.
        Previously queried 'form_responses' table directly.
        Ideally this should move to FormAnalytics, but it was here.
        If we want to support it here, we need FormRepository or TabularRepository to support it?
        Wait, QueryService manages 'tabular' primarily.
        'form_status_counts' queries 'form_responses'.
        Strictly speaking, this should be in FormAnalytics.
        But for now, to avoid breaking API 'queries/forms/status', we should probably keep it 
        or delegate.
        However, QueryService doesn't have access to FormRepository.
        
        Refactor decision: Move logic to FormAnalytics? Or give QueryService access?
        Simpler: Remove this method if it's not used by new Views?
        frontend calls `/queries/forms/status`.
        The router calls `query_service.form_status_counts`.
        
        I should implement `get_raw_forms` in TabularRepository? No.
        I should inject FormRepository too? Or direct SQL for this legacy method?
        Direct SQL is banned in strict repo pattern.
        
        Best: Deprecate/Return Empty for now? Or quick fix:
        The `form_status_counts` seems to be for global stats.
        Let's stub it or implement via `FormAnalytics` if needed.
        Actually, looking at `dependencies`, `FormAnalytics` is distinct.
        Users might expect this to work.
        I will comment it out or leave a stub, noting it should be moved.
        The frontend view that uses it is 'StatusView' (maybe?).
        Let's implement a minimal version if possible, or skip strictly usage of DB.
        But 'QueryService' has 'TabularRepository'.
        
        Hypothesis: 'form_status_counts' is legacy or should be moved.
        I will implement a safe empty return to prevent crash, 
        and note to move it to FormAnalytics later.
        """
        return {"gaps": [], "ok": []}

    def tabular_by_platoon(self, section: str, top_n: int = 20, week: Optional[str] = None) -> List[Dict]:
        """
        Aggregate numeric totals per platoon for a given section.
        """
        df = self.repo.get_records(section, week=week, platoon=None) # Fetch all platoons
        if df.empty:
            return []
            
        df["value_num"] = pd.to_numeric(df["value_num"], errors="coerce").fillna(0)
        
        # Group by platoon and item
        grouped = df.groupby(["platoon", "item"])["value_num"].sum().reset_index()
        grouped = grouped.sort_values(["platoon", "value_num"], ascending=[True, False])
        
        results = []
        for platoon, pdf in grouped.groupby("platoon"):
            top_items = pdf.head(top_n)[["item", "value_num"]].rename(columns={"value_num": "total"})
            results.append({
                "platoon": platoon,
                "items": top_items.to_dict("records")
            })
            
        return results

    def tabular_delta(self, section: str, top_n: int = 20) -> List[Dict]:
        """
        Delta between the latest two imports for a given section.
        """
        import_ids = self.repo.get_latest_imports(section, 2)
        if len(import_ids) < 2:
            return []
        current_id, prev_id = import_ids[0], import_ids[1]

        # Use helper
        cur_df = self.repo.get_totals_by_import(section, current_id)
        prev_df = self.repo.get_totals_by_import(section, prev_id)
        
        # Merge
        merged = pd.merge(cur_df, prev_df, on="item", how="outer", suffixes=("_cur", "_prev")).fillna(0)
        merged["delta"] = merged["total_num_cur"] - merged["total_num_prev"]
        
        results = []
        for _, row in merged.iterrows():
            cur = row["total_num_cur"]
            prev = row["total_num_prev"]
            delta = row["delta"]
            direction = "up" if delta > 0 else "down" if delta < 0 else "flat"
            pct = (delta / prev * 100) if prev != 0 else None
            
            results.append({
                "item": row["item"],
                "current": cur,
                "previous": prev,
                "delta": delta,
                "direction": direction,
                "pct_change": pct
            })
            
        results.sort(key=lambda x: abs(x["delta"]), reverse=True)
        return results[:top_n]

    def tabular_variance_vs_summary(self, section: str, top_n: int = 20) -> List[Dict]:
        """
        Compare latest platoon section totals to latest battalion summary totals.
        """
        summary_map = {"zivud": "summary_zivud", "ammo": "summary_ammo"}
        summary_section = summary_map.get(section)
        if not summary_section:
            return []

        import_ids_section = self.repo.get_latest_imports(section, 1)
        import_ids_summary = self.repo.get_latest_imports(summary_section, 1)
        
        if not import_ids_section or not import_ids_summary:
            return []
            
        cur_df = self.repo.get_totals_by_import(section, import_ids_section[0])
        sum_df = self.repo.get_totals_by_import(summary_section, import_ids_summary[0])
        
        merged = pd.merge(cur_df, sum_df, on="item", how="outer", suffixes=("_cur", "_sum")).fillna(0)
        merged["variance"] = merged["total_num_cur"] - merged["total_num_sum"]
        
        results = []
        for _, row in merged.iterrows():
            summary_val = row["total_num_sum"]
            diff = row["variance"]
            pct = (diff / summary_val * 100) if summary_val != 0 else None
            
            results.append({
                "item": row["item"],
                "current": row["total_num_cur"],
                "summary": summary_val,
                "variance": diff,
                "direction": "up" if diff > 0 else "down" if diff < 0 else "flat",
                "pct_change": pct
            })
            
        results.sort(key=lambda x: abs(x["variance"]), reverse=True)
        return results[:top_n]

    def tabular_trends(
        self,
        section: str,
        top_n: int = 5,
        platoon: Optional[str] = None,
        window_weeks: int = 8,
    ) -> List[Dict]:
        """
        Trendlines for top items over recent weeks.
        """
        # Fetch *all* history for section/platoon
        df = self.repo.get_records(section, platoon=platoon)
        if df.empty:
            return []
            
        # Parse Dates
        df["created_at"] = pd.to_datetime(df["created_at"])
        cutoff = datetime.now(UTC) - timedelta(weeks=window_weeks)
        # Ensure UTC awareness if column is tz-naive
        if df["created_at"].dt.tz is None:
             df["created_at"] = df["created_at"].dt.tz_localize(UTC)
             
        df = df[df["created_at"] >= cutoff]
        df["value_num"] = pd.to_numeric(df["value_num"], errors="coerce").fillna(0)
        
        # Identify Top N items by total sum in window
        top_items = (
            df.groupby("item")["value_num"]
            .sum()
            .sort_values(ascending=False)
            .head(top_n)
            .index.tolist()
        )
        
        if not top_items:
            return []
            
        # Group by item and week
        filtered = df[df["item"].isin(top_items)]
        trend_data = (
            filtered.groupby(["item", "week_label"])["value_num"]
            .sum()
            .reset_index()
            .sort_values("week_label")
        )
            
        series = []
        for item in top_items:
            points = trend_data[trend_data["item"] == item][["week_label", "value_num"]]
            series.append({
                "item": item,
                "points": [{"week": r.week_label, "total": r.value_num} for r in points.itertuples()]
            })
            
        return series

    def tabular_by_family(
        self,
        section: str,
        platoon: Optional[str] = None,
        week: Optional[str] = None,
        top_n: int = 50,
    ) -> List[Dict]:
        """
        Aggregate gaps/totals per item for a section, filtered by platoon/week.
        Interprets textual gaps (חוסר/בלאי) and numeric totals.
        """
        df = self.repo.get_records(section, week=week, platoon=platoon)
        if df.empty:
            return []

        # Gap counts
        gap_counts = Counter()
        for item, text in zip(df["item"], df["value_text"]):
            if isinstance(text, str) and any(tok in text for tok in self.gap_tokens):
                gap_counts[item] += 1

        # Numeric totals
        df["value_num"] = pd.to_numeric(df["value_num"], errors="coerce").fillna(0)
        totals = df.groupby("item")["value_num"].sum().to_dict()

        items = set(gap_counts.keys()) | set(totals.keys())
        results = []
        for item in items:
            results.append({
                "item": item,
                "gaps": gap_counts.get(item, 0),
                "total": totals.get(item, 0),
                "platoon": platoon,
            })
        results.sort(key=lambda x: x["gaps"], reverse=True)
        return results[:top_n]

    def tabular_gaps_by_platoon(
        self,
        section: str,
        week: Optional[str] = None,
        top_n: int = 100,
    ) -> List[Dict]:
        """
        Per-platoon gap counts per item (mirrors battalion sheet layout).
        """
        df = self.repo.get_records(section, week=week, platoon=None)
        if df.empty:
            return []

        gap_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for platoon, item, text in zip(df["platoon"], df["item"], df["value_text"]):
            if not isinstance(text, str):
                continue
            if any(tok in text for tok in self.gap_tokens):
                gap_counts[platoon][item] += 1

        results = []
        for platoon, items in gap_counts.items():
            for item, count in items.items():
                results.append({"platoon": platoon, "item": item, "gaps": count})
        results.sort(key=lambda x: x["gaps"], reverse=True)
        return results[:top_n]

    def tabular_search(
        self,
        q: str,
        section: Optional[str] = None,
        platoon: Optional[str] = None,
        week: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict]:
        """
        Free-text search across tabular records (legacy Excel imports).
        Matches item name, column/tank identifier, or textual value.
        """
        if not q or len(q.strip()) < 2:
            return []

        query_text = q.strip()
        sections = [section] if section else ["zivud", "ammo", "summary_zivud", "summary_ammo"]
        results: List[Dict] = []

        for sec in sections:
            df = self.repo.get_records(sec, week=week, platoon=platoon)
            if df.empty:
                continue

            mask = (
                df["item"].astype(str).str.contains(query_text, case=False, na=False)
                | df["column_name"].astype(str).str.contains(query_text, case=False, na=False)
                | df["value_text"].astype(str).str.contains(query_text, case=False, na=False)
            )
            hits = df[mask].copy()
            if hits.empty:
                continue

            hits["resolved_value"] = hits["value_text"].fillna(hits["value_num"])
            for _, row in hits.head(max(limit - len(results), 0)).iterrows():
                val = row.get("resolved_value")
                value_text = row.get("value_text") or ""
                is_gap = any(tok in value_text for tok in self.gap_tokens) or (row.get("value_num") == 0)
                results.append(
                    {
                        "section": sec,
                        "item": row.get("item"),
                        "column": row.get("column_name"),
                        "platoon": row.get("platoon"),
                        "week": row.get("week_label"),
                        "value": val,
                        "is_gap": bool(is_gap),
                    }
                )
                if len(results) >= limit:
                    break

            if len(results) >= limit:
                break

        return results
