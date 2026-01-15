# Spearhead 2.0: Technical Roadmap & Implementation Guide

> **Version**: 2.0.0-PLAN
> **Date**: 2026-01-14
> **Objective**: Transition from Prototype to Operational System ("Mochacht Mivtzayi").

## 🎯 Strategic Vision: "Data First, Then Polish"

The immediate priority is **Operational Relevance**. The system must display correct, relevant data to the commander immediately upon login. We achieve this by:

1.  **Ensuring Data Ingestion Works**: Fixing filename parsing logic so files aren't rejected.
2.  **Displaying the Right View**: Strictly separating "Battalion Command" (Aggregates) from "Platoon Tactical" (Gaps).
3.  **Stabilizing the Platform**: Fixing the infinite loop crash.

---

## 🏗️ Architectural Changes

### 1. Frontend: "Context-Aware Views"

We are moving away from a monolithic `DashboardContent` to a modular View Architecture.

- **`src/views/BattalionView.jsx`**:
  - **Purpose**: High-level command overview.
  - **Components**: `KpiStrip`, `SummaryTable` (Aggregated Totals).
  - **Hidden**: Platoon-specific drill-down cards.
  - **Data Source**: `GET /queries/tabular/by-platoon`.
- **`src/views/PlatoonView.jsx`**:
  - **Purpose**: Tactical drill-down for specific shortages.
  - **Components**: `GapCard`, `IssuesTable` (Specific Item Anomalies).
  - **Data Source**: `GET /queries/tabular/gaps`, `GET /queries/forms/gaps`.
- **`src/hooks/useAutoSync.js`**:
  - **Purpose**: "Invisible Sync" - "Push" model.
  - **Logic**: Triggers `syncMutation` on successful authentication.

### 2. Backend: "Sterile & Layered"

We will refactor the "God Class" (`QueryService`) into a proper layered architecture.

- **Repository Layer** (`src/spearhead/data/repositories.py`):
  - Pure SQL execution.
  - Methods: `get_battalion_totals()`, `get_platoon_gaps(platoon)`.
- **Service Layer** (`src/spearhead/services/`):
  - Orchestration & Security Enforcement.
  - **Tenant Isolation**: Logic that checks `current_user.platoon` and _forces_ the filter on Repository calls.
- **Domain Layer** (`src/spearhead/logic/`):
  - Gap definitions, Erosion scoring formulae.

---

## 📅 Phased Execution Plan

### 🚨 Phase 1: Data Visibility & Stability (Immediate)

_Goal: The user logs in and sees relevant numbers immediately._

#### 1.1 Prerequisite: Hygiene

- [ ] **Delete Garbage**: Remove `notebook_*.py`, legacy scripts (`config 2.py`), and unused assets to clear the workspace.

#### 1.2 Prerequisite: Stability & Ingestion

- [ ] **Fix Frontend Loop**: Debug `MainLayout.jsx` / `useOAuthLanding` to strictly limit re-renders.
- [ ] **Fix Ingestion Logic**: Update `FieldMapper.infer_platoon` in `src/spearhead/data/field_mapper.py` to handle:
  - Suffixes: `(תגובות)`, `(Copy)`, `(1)`.
  - Hebrew Filenames: Robust matching for "כפיר", "סופה" within complex strings.
- [ ] **Verify**: Upload a "dirty" filename file and confirm it maps to the correct platoon.

#### 1.3 Implement "Relevant Query Views"

- [ ] **Create `BattalionView.jsx`**: Implement the aggregate summary view.
- [ ] **Create `PlatoonView.jsx`**: Implement the detailed gap view.
- [ ] **Refactor `DashboardContent.jsx`**:
  - If `viewMode == 'battalion'`: Render `BattalionView`.
  - If `viewMode == 'platoon'`: Render `PlatoonView`.
- [ ] **Verify**: Login as Battalion -> See Totals. Login as Platoon -> See Gaps.

### 🔄 Phase 2: "Invisible Sync" (UX)

_Goal: Frictionless updates._

- [ ] **Auto-Sync Hook**: Create `useAutoSync` that runs _once_ on auth.
- [ ] **Remove UI Button**: Delete the manual "Search/Sync" button from `HeroHeader`.
- [ ] **Status Indicator**: Add a subtle "Syncing / Up to date" indicator in the top bar.

### 🛡️ Phase 3: Backend Architecture (Sterility)

_Goal: Security and Code Health._

- [ ] **Create `repositories.py`**: Migrate SQL from `QueryService`.
- [ ] **Enforce Security**: Inject `CurrentUser` into all services and force `platoon={current_user.platoon}` filters in the Repository layer.

### 🧠 Phase 4: Advanced Analytics (Intelligence)

_Goal: Decision Support - "Spearhead Intelligence"._

- [ ] **Stats Engine**: Implement `src/spearhead/logic/stats.py` for weighted scoring and trend regression.
- [ ] **Intelligence Service**: Orchestrate data fetching and math to produce:
  - **Readiness Score**: 0-100% based on weighted Tank/Zivud/Ammo status.
  - **Trends**: Line charts showing gap reduction over time.
  - **Anomalies**: Statistical deviation detection (Z-Score).

### 📄 Phase 5: Reports (Polish)

_Goal: Commander-ready documentation._

- [ ] **Excel Styling**: Implement `apply_active_duty_styling()` in `exporter.py` (Borders, RTL, Bold Headers, Conditional Formatting for Gaps).

---

## ✅ Definition of Done (v2.0)

1.  **Zero Crashes**: Dashboard loads instantly.
2.  **No "Sync" Button**: Data updates automatically.
3.  **Distinct Views**: Battalion view never shows Platoon Cards; Platoon view shows Gaps.
4.  **Sterile Data**: A "Kfir" user cannot access "Sufa" data via API hacking.
5.  **Clean Repo**: No junk files.
