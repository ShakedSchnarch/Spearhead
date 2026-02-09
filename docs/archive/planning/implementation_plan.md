# Implementation Plan - Phase 4: Advanced Analytics (Spearhead Intelligence)

## Goal

End-to-end implementation of an "Intelligence Engine" and high-end visualization users.
**Principle**: "Contract First" -> "Logic Core" -> "Service Orchestration" -> "UI Components".

## User Review Required

> [!IMPORTANT] > **Scoring Weights Configuration**:
>
> - **Material (Zivud)**: 40% impact.
> - **Ammo**: 30% impact.
> - **Completeness**: 30% impact.
> - **Veto (Critical)**: Score = 0 if engine/shooting/comms are "Not OK".

## Detailed Execution Steps

# Implementation Plan: Realignment & Handover Protocol

## Goal

To stabilize the "Spearhead 2.0" system, ensuring strict consistency between the Database, Backend Services, and Frontend UI, and proving "Data Visibility" to the user.

## Active Remediation Protocol (Phase 6)

### 1. Fix Visual Disconnect (Priority Alpha)

- [x] **Debug Response**:
  - [x] Action: Log full JSON response from `GET /intelligence/platoon/{id}`.
  - [x] Check: Verify `readiness_score`, `critical_gaps`, `top_issues` keys exist.
- [x] **Update Component**:
  - [x] Action: Modify `PlatoonView.jsx` to map exact API keys to props.
  - [x] Action: Ensure `ReadinessGauge` handles `0` or `null` gracefully (don't crash, show "No Data").

### 2. Restore "Legacy" Data Access

- [x] **Query Interface**:
  - [x] Action: Create `src/components/QueryBar.jsx`. (Implemented as `QueryPanel` wired to search endpoint.)
  - [x] Action: Connect to `QueryService` endpoints (`/queries`).
  - [x] Goal: Allow user to type "Mag" and see which tanks are missing it (from the legacy Excel import).
- [x] **Status Tables**:
  - [x] Action: Use `TabularRepository` to fetch raw counts for the "Battalion Summary" table.
  - [x] Goal: Show actual numbers (e.g., "Total Ammo: 50,000") derived from `raw_tabular` table.

### 3. Commander Reports (The Output)

- [ ] **Style Verification**:
  - [x] Action: Review `excel_styles.py`. check `Side(style='thin')` and `Alignment(horizontal='right')`.
  - [x] Action: Generate test report.
  - [ ] Goal: Digital copy of the user's manual reports.

## Data Recon: Legacy Week 3 Files (do not depend on them, but mirror logic)

- Files parsed: `Old_Files_To_Learn_from/דוחות פלוגת כפיר.xlsx`, `.../סופה.xlsx`, `.../מחץ.xlsx`, `מסמך דוחות גדודי.xlsx` (sheet "שבוע 3").
- Platoon sheets structure:
  - **Kfir**: Zivud table with columns `[הפריט, תקן, צ' <tank> ...]`, values are text tokens (`קיים`, `חוסר`, `בלאי`, sometimes numeric). No per-row totals, pure tank matrix.
  - **Mahatz**: Same matrix but includes per-row totals (`סה\"כ תקין/בלאי/חוסר`) ahead of tank columns. Tokens are mixed Hebrew text; totals are numeric counts.
  - **Sufa**: Matrix plus per-row summary text like `"7 קיים, 1 בלאי, 0 חוסר"` in the last column; tank columns similar to above.
  - All sheets have an ammo/armament section further down (keywords: `מאג`, `פגזים`, `רימון`, etc.) with serials/quantities per tank; some rows have equipment IDs + status.
  - Additional comms/optics rows (e.g., `NFC`, `בורוסייט`, `מדיה\\נר לילה`) with status + location fields per tank.
- Battalion sheet:
  - Zivud gaps per platoon columns (`חוסרים\\בלאי <platoon>`, `חוסרים\\בלאי גדודי`) and ammo summary columns (`סה\"כ <platoon>`, `ממוצע לטנק <platoon>`).
  - Provides template for battalion-level aggregates: per-item gap counts by platoon and per-platoon ammo totals/averages.

## Target Architecture & Roadmap (Phase 6+)

### A. Frontend layering (modular, no rewrites)
- **Data mappers**: Normalize API payloads into view models (platoon/battalion) so components are dumb and swappable.
- **Hooks separation**: `useIntelligence` (scores/trends), `useQueries` (tabular/search), `useReports` (exports). Avoid coupling to DashboardContext.
- **Components to add**:
  - Platoon: Tank readiness grid (per tank overall + per-family breakdown: ציוד/תחשוב/חימוש), weekly delta widget, reporting coverage widget, trend sparkline per tank, AI placeholder panel.
  - Battalion: Per-platoon readiness table + mini sparkline, platoon delta vs previous week, aggregated gap table (top items with counts), trends by platoon.
  - Shared: QueryPanel (done), TotalsCard (legacy counts), TrendChart (Recharts/Mantine), StatusPills for gaps/bloi tokens.
- **Scope enforcement**: Respect view mode for all widgets (query/search/export/intelligence) via context-aware hooks.

### B. Backend services (incremental, scoped)
- **Analytics layer**: Extend `FormAnalytics`/`IntelligenceService` to emit:
  - Per-tank per-family scores (ציוד/תחמושת/תקשוב/כולל).
  - Weekly deltas: current vs previous week per tank/platoon.
  - Trends: last N weeks per tank and per platoon (readiness, gaps).
  - Reporting coverage: counts of reports per week/tank.
- **QueryService**:
  - Keep tabular search (done); add per-family aggregation endpoints (totals, gaps) aligned with legacy schemas.
  - Battalion aggregate endpoint mirroring battalion Excel: per-item gap counts by platoon + ammo totals/avg per platoon.
- **DTO contracts**: Versioned schemas for PlatoonIntelligence/BattalionIntelligence to include breakdowns, deltas, trends; mappers in frontend consume these.

### C. Execution plan (with approval gates)
1) **Data model & contract draft** (no code): Document API payload shapes for new widgets (per tank/platoon, deltas, trends). Get approval.
2) **Backend extensions**: Implement analytics computations (deltas/trends/breakdowns), add endpoints/fields without breaking existing ones. Prove with sample JSON + tests. Approval gate.
3) **Frontend mapping**: Add data mappers/hooks, wire new DTO fields, build platoon widgets (tank grid, deltas, trends). Show screenshots/JSON proof. Approval gate.
4) **Battalion widgets**: Add aggregates (per-platoon readiness, gap table, trends), ensure scope handling. Approval gate.
5) **Polish & reports**: Final Excel visual check, RTL/borders confirmed. Approval gate before release.

## V2 API/DTO Contract Draft (pending coding)

### Principles
- Keep existing fields; append new keys for V2 data to avoid breakage.
- Enforce scope server-side (platoon vs battalion) and surface scope in payload.
- Metrics from DB (forms/tabular), legacy files only inform grouping and labels.

### Platoon Intelligence (GET `/intelligence/platoon/{platoon}?week=YYYY-Www`)
```json
{
  "platoon": "כפיר",
  "week": "2026-W03",
  "readiness_score": 87.9,
  "breakdown": {
    "zivud": 84.0,
    "ammo": 89.0,
    "comms": 90.0,
    "completeness": 100.0
  },
  "deltas": { "overall": -2.1, "zivud": -3.0, "ammo": 1.5, "comms": 0.0 },
  "coverage": { "reports_this_week": 11, "expected": 11, "missing_reports": 0 },
  "tank_scores": [
    {
      "tank_id": "צ'653",
      "score": 87.9,
      "grade": "B",
      "family_breakdown": {
        "zivud": 80.0,
        "ammo": 86.3,
        "comms": 95.0,
        "completeness": 100.0
      },
      "deltas": { "overall": -1.0, "zivud": -2.0, "ammo": 0.5, "comms": 0.0 },
      "critical_gaps": ["חוסר ג'ק ערבי"],
      "top_missing_items": ["שרשרת גרירה", "שאקל 25 טון"],
      "gap_counts": { "zivud": 3, "ammo": 1, "comms": 0 },
      "trend": [
        { "week": "2026-W01", "score": 90.0, "gaps": 2 },
        { "week": "2026-W02", "score": 88.9, "gaps": 3 },
        { "week": "2026-W03", "score": 87.9, "gaps": 4 }
      ]
    }
  ],
  "top_gaps_platoon": [
    { "item": "שרשרת גרירה", "gaps": 4, "family": "zivud" },
    { "item": "מאג", "gaps": 2, "family": "ammo" }
  ]
}
```
- Families: `zivud`, `ammo`, `comms` (optics/tech), `completeness`.
- `trend` uses `week_label`, `gaps` = count of missing/bloi tokens for that tank/week.

### Battalion Intelligence (GET `/intelligence/battalion?week=YYYY-Www`)
```json
{
  "week": "2026-W03",
  "overall_readiness": 85.2,
  "deltas": { "overall": -1.5 },
  "platoons": {
    "כפיר": {
      "readiness_score": 87.9,
      "delta": -2.1,
      "gaps_by_family": { "zivud": 15, "ammo": 4, "comms": 1 },
      "coverage": { "reports": 11, "missing": 0 },
      "trend": [
        { "week": "2026-W01", "score": 90.0 },
        { "week": "2026-W02", "score": 89.0 },
        { "week": "2026-W03", "score": 87.9 }
      ]
    }
  },
  "comparison": { "כפיר": 87.9, "סופה": 84.0, "מחץ": 83.5 },
  "top_gaps_battalion": [
    { "item": "שרשרת גרירה", "platoons": { "כפיר": 4, "סופה": 2, "מחץ": 1 } },
    { "item": "מאג", "platoons": { "מחץ": 3 } }
  ]
}
```

### Query/Tabular (new/extended)
- `GET /queries/tabular/by-family`: `{ section=zivud|ammo|comms, platoon?, week? } -> [{ item, gaps, total, platoon }]`
- `GET /queries/tabular/gaps-by-platoon`: `{ section, week? } -> [{ platoon, item, gaps }]` (mirrors battalion sheet gap columns).
- `GET /queries/tabular/search`: keep (free text across item/column/value).
- `GET /queries/forms/coverage`: keep; feeds reporting coverage widgets.

### Calculations
- **Weights**: current (zivud 40%, ammo 30%, completeness 30). Proposal for V2 with comms: zivud 30, ammo 30, comms 20, completeness 20 (to confirm with user). Include weights in response metadata.
- **Gaps**: tokenize `חוסר/בלאי` (config-driven) per tank/item; aggregate per family.
- **Deltas**: current week score minus previous week at same scope (tank/platoon).
- **Trends**: last N weeks (default 8) using `week_label`.
- **Coverage**: form count per tank/week vs expected distinct tanks in scope.

### Frontend mapping targets
- Platoon:
  - Tank grid uses `tank_scores.family_breakdown`, `deltas`, `trend`.
  - KPIs use `readiness_score`, `deltas`, `coverage`.
  - Gap table uses `top_gaps_platoon`.
  - Trend sparklines use per-tank `trend`.
- Battalion:
  - Comparison chart uses `comparison`.
  - Delta badges per platoon use `platoons[*].delta`.
  - Gap table uses `top_gaps_battalion`.
  - Trends per platoon use `platoons[*].trend`.

### Scope & Auth
- If `user.platoon` is set and not `battalion`, API filters to that platoon; battalion endpoint 403 for platoon users.
- Query endpoints auto-scope to `user.platoon` when present.

## Completed Features (Reference)

- **Intelligence Engine**: Weighted scoring logic.
- **Excel Reports**: "Commander Style" formatting.
- **Tenant Isolation**: Strict platoon-level data access.
