# Spearhead 2.0 Technical Roadmap

This roadmap outlines the transformation of Spearhead into a robust, "Tactical" Grade command system. It is divided into three distinct phases to ensure stability before complexity.

## Phase 6: Core Infrastructure & Sterility (The Foundation)

**Goal**: Ensure data is ingested correctly and isolated strictly between units. No UI changes yet, just plumbing.

### 6.1 Robust Data Ingestion

**Problem**: Current regex logic is fragile (e.g., `(תגובות)` suffix causes 404).
**Plan**:

- [ ] **Refactor `FieldMapper.infer_platoon`**:
  - Implement a `Clean-Normalize-Match` pipeline.
  - **Step 1**: Strip known "noise" suffixes: `(תגובות)`, `(Responses)`, `_export`.
  - **Step 2**: Tokenize and match against a **Strict Allowlist** of units (`config.yaml`): `["כפיר", "להב", "מחץ", "חוד", "מפקדה"]`.
  - **Step 3**: Fallback to "Unknown" (Log warning) instead of random filename tokens.
- **Verification**: Unit tests with real-world filename examples.

### 6.2 Sterile Authorization (Tenant Isolation)

**Problem**: Current auth protects the _API_ but not the _Data_. "Kfir" user can query "Lahav" data.
**Plan**:

- [ ] **Data Model**: Introduce `User` context in `deps.py`.
  - `User(role="commander", unit="kfir")` or `User(role="admin", unit="all")`.
- [ ] **Enforcement Middleware**:
  - In `queries.py`, check: `if user.unit != 'all' and user.unit != request.platoon: raise 403`.
  - Apply this to **ALL** endpoints (Forms, Summaries, Exports).
- **Decision Point**: For now, map `BASIC_USER_KFIR` env var to unit "kfir". Later upgrade to DB-backed users.

---

## Phase 7: Analytics Engine - "The Brain" (The Logic)

**Goal**: Move from "Counting Gaps" to "Operational Readiness Scores".

### 7.1 Weighted Scoring Module (`src/spearhead/logic/scoring.py`)

**Concept**: Not all gaps are equal. A missing engine is worse than a missing jerrycan.
**Plan**:

- [ ] **Define Weights**:
  - `CRITICAL` (Engine, Fire Control, Comms): -20 pts.
  - `MAJOR` (Optics, MAG): -5 pts.
  - `MINOR` (Jerrycan, Net): -1 pt.
- [ ] **Algorithm**:
  - `Base Score = 100`
  - `Score = Max(0, 100 - Sum(Weighted Gaps))`
  - Calculate per Tank -> Average per Platoon -> Average per Battalion.

### 7.2 Compliance Service

**Problem**: We don't know who _didn't_ submit a report.
**Plan**:

- [ ] **Registry**: Define `EXPECTED_UNITS = ["kfir", "lahav", "mahatz", "hod"]`.
- [ ] **Logic**: Compare `DISTINCT platoon FROM responses WHERE week=X` vs `EXPECTED_UNITS`.
- [ ] **Output**: `{ "missing": ["lahav"], "complete": ["kfir"] }`.

### 7.3 Trend Analysis

**Plan**:

- [ ] **Delta Calculation**: Calculate `Score(Week X) - Score(Week X-1)`.
- [ ] **Insight Generation**: "Kfir improved by 5% readiness this week".

---

## Phase 8: "Command Cockpit" - UX Overhaul (The View)

**Goal**: Implement the "Tactical Flat" design language (Dark Mode, Glassmorphism, Concise).

### 8.1 Design System Implementation

**Plan**:

- [ ] **Tokens**: Define CSS variables for `primary-emerald`, `danger-rose`, `bg-slate-900`.
- [ ] **Components**:
  - `TacticalCard`: Glassmorphism container.
  - `StatusBadge`: Neon glow effect for statuses.
  - `MetricGauge`: Circular/Linear progress bars.

### 8.2 Dashboard Layout ("Cockpit")

**Plan**:

- [ ] **Top Bar**: "Defcon" status, Last Refresh, Current User Context.
- [ ] **KPI Row**:
  - **Readiness**: Big % number with trend arrow.
  - **Critical Faults**: Red counter.
  - **Compliance**: "3/4 Units Reported".
- [ ] **Main View**:
  - **Battalion**: Compare Platoons (Bar Chart).
  - **Platoon**: Tank List sorted by _Readiness Score_ (ascending - worst first).
- [ ] **AI Feed Sidebar**: Natural language insights stream.

### 8.3 "Red List" Table

**Plan**:

- [ ] Focus on _Anomalies_. Show only tanks with Score < 80% or Critical Faults.
- [ ] Columns: Tank ID | Unit | Critical Issues | AI Remark.

---

## Milestones & Checkpoints

1.  **Checkpoint 1 (Core)**: Ingestion works for "Kfir" file. Admin sees all, Kfir user sees only Kfir.
2.  **Checkpoint 2 (Logic)**: API returns `readiness_score` and `compliance_status`.
3.  **Checkpoint 3 (UX)**: Dashboard looks like the mockup.
