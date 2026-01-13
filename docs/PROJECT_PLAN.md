# Spearhead 2.0 - Project Plan

**Vision**: A "Tactical Grade" operational dashboard for Battalion Command (Magad/Samgad).  
**Core Principles**:

1.  **Isolation ("Sterility")**: A Platoon Commander sees _only_ their data. Battalion Command sees all.
2.  **Readiness Score**: Move from "counting gaps" to a weighted 0-100% operational score.
3.  **Tactical UX**: Dark mode, high contrast, focus on anomalies ("Red List").
4.  **Resilience**: Robust ingestion that handles messy filenames and missing data gracefully.

---

## 🏗 Phase 6: Core Infrastructure & Sterility (Foundation)

**Goal**: The system is unbreakable and secure.

### 6.1 Robust Data Ingestion

Current Issue: Filenames like `...כפיר (תגובות).xlsx` cause data to be lost or mislabeled.

- [ ] **Refactor `FieldMapper.infer_platoon`**:
  - Strip suffixes: `(תגובות)`, `(Responses)`, `_export`.
  - **Allowlist Match**: Explicitly map filenames `*kfir*`, `*כפיר*` → `Unit: Kfir`.
  - **Fallback**: Log warning for unknown files instead of guessing.

### 6.2 Sterile Authorization (Tenant Isolation)

Current Issue: A valid token allows access to all data.

- [ ] **User Context**: Introduce `User(id, unit, role)` model.
- [ ] **Enforcement**:
  - Middleware/Dependency: `require_platoon_access(platoon_name)`.
  - If `User.unit != 'all'` AND `User.unit != platoon_name` → **403 Forbidden**.
  - Apply to **Exports**, **Summaries**, and **Trends**.

---

## 🧠 Phase 7: Analytics Engine ("The Brain")

**Goal**: Insights, not just raw data.

### 7.1 Weighted Readiness Score

- [ ] **Scoring Module (`scoring.py`)**:
  - Base: 100 points.
  - **Critical Fault** (Engine, Fire Control): -20 pts.
  - **Major Fault** (Optics, Comm): -5 pts.
  - **Minor Fault** (Jerrycan, Net): -1 pt.
- [ ] **Metrics**: Calculate `Readiness %` per Tank, Platoon, and Battalion.

### 7.2 Compliance & Trends

- [ ] **ComplianceService**:
  - Input: List of expected units (Structure).
  - Output: Who reported this week? Who is missing?
- [ ] **Trend Analysis**:
  - Compare `Score(Current Week)` vs `Score(Last Week)`.
  - Output: "Improving (+5%)" or "Eroding (-10%)".

---

## 💎 Phase 8: "Command Cockpit" UX Overhaul

**Goal**: A UI that looks and feels like a weapon system.

### 8.1 Design System ("Tactical Flat")

- [ ] **Theme**: Slate-900 Background, Emerald-500 (OK), Rose-500 (Fault), Amber-500 (Warning).
- [ ] **Glassmorphism**: Translucent cards with subtle borders.

### 8.2 Dashboard Layout

1.  **Top Bar**: DEFCON status, Last Sync time, User Unit.
2.  **KPI Row**:
    - **Readiness**: Big Gauge (e.g., "88%").
    - **Critical Faults**: Red Counter.
    - **Compliance**: "3/4 Units".
3.  **Main View**:
    - **Battalion Mode**: Bar chart comparing platoons.
    - **Platoon Mode**: "Red List" (Focus on worst tanks first).

### 8.3 The "Red List"

- A focused table showing ONLY tanks with issues.
- Columns: `Tank ID` | `Score` | `Critical Gaps` | `Commander`.
- Action: "Export for Technician".

---

## 📜 Milestones

1.  **Infrastructure Fixed**: Ingestion works for all files, Auth blocks unauthorized access.
2.  **Logic Implemented**: API returns Scores and Compliance.
3.  **UX Deployed**: Dashboard reflects new design.
