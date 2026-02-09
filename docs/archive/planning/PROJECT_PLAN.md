# Spearhead Project Plan & Status

> **Last Updated**: 2026-01-13
> **Status**: Freezing Phase 1. Preparing for Phase 2 (Refinement).

## 1. Completed Phase (Foundation & Debugging)

- [x] **Robust Data Ingestion**
  - [x] Update `FieldMapper` to robustly infer platoon
  - [x] Config: Explicit Platoon-to-ID Mapping (Fix "None" issue)
  - [x] Backend: Support Dictionary Configuration
- [x] **Sterile Authorization**
  - [x] Implement User Context & Tenant Isolation
  - [x] Fix 500/403 Error Handling
- [x] **Core Functionality**
  - [x] Google Sheets Sync (Manual)
  - [x] Excel Export (Platoon & Battalion)
  - [x] SPA Routing & Server Stability

## 2. Phase 5: Refinement & User Experience (Next Steps)

- [ ] **Workflow Automation**
  - [ ] **Auto-Sync on Login**: Remove manual sync button; trigger background sync immediately upon successful auth.
  - [ ] **Context-Aware Dashboard**:
    - [ ] **Battalion View**: Hide granular platoon cards? Show high-level summary only.
    - [ ] **Sync Logic**: Disable/Hide sync controls when in Battalion view looking at Platoon specific mode?
- [ ] **Export Excellence**
  - [ ] **Format Overhaul**: Improve Excel styling (headers, colors, column widths).
  - [ ] **Content**: Ensure export matches user expectations (fields, totals).
- [ ] **Project Hygiene**
  - [x] Cleanup junk files (`config 2.py`, debug scripts).
  - [ ] **Further Cleanup**: Review unused frontend components (e.g., `UploadCard` if deprecated).
- [ ] **Docs & Freeze**
  - [ ] Update `implementation_plan.md` with detailed spec for formatted exports.
  - [ ] Git Commit 1.0 Stable.

## 3. Future Phases (Tactical)

- [ ] **Phase 3: Tactical Features**:
  - [ ] **Tank Grid**: Visual representation of assets instead of tables.
  - [ ] **Logistics Shopping List**: Dedicated view for supply gaps.
