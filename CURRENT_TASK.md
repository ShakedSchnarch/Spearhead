# IronView v1.0 Roadmap

## Phase 2: Auth Checkpoints & Sync Hardening

Focus on securing the application and ensuring data sync is robust and transparent.

- [x] **Backend: OAuth & Session Architecture** <!-- id: 5 -->
  - [x] Implement `RefreshToken` mechanism in `OAuthSessionStore` with TTL. <!-- id: 5.1 -->
  - [x] Add background cleanup job for expired sessions (Implicit via `_purge` on set/get). <!-- id: 5.2 -->
  - [x] Update `/sync/status` endpoint to expose `auth_mode` (User vs Service) and `source` information. <!-- id: 5.3 -->
- [x] **Frontend: Auth Experience** <!-- id: 6 -->
  - [x] Split `session` (OAuth metadata) from `apiToken` in `DashboardContext`. <!-- id: 6.1 -->
  - [x] Update `LoginOverlay` to clearly show "Sync Ready" vs "Offline Mode" (Verified redundant, `HeroHeader` handles this). <!-- id: 6.2 -->
  - [x] Implement 401/403 Error Handling: Auto-redirect to login via `useApiClient` interceptor. <!-- id: 6.3 -->
  - [x] Pass `X-OAuth-Session` header on all Sync API calls. <!-- id: 6.4 -->
- [x] **Verification** <!-- id: 7 -->
  - [x] Test OAuth expiry and refresh flow (Logic implemented & Unit tests passed). <!-- id: 7.1 -->

## Phase 3: Data Integrity & Exports

Focus on the accuracy of the reports and the flexibility of data extraction.

- [x] **Data Verification** <!-- id: 8 -->
  - [x] Verify "Latest Week" logic across all summary/coverage endpoints. <!-- id: 8.1 -->
  - [x] Ensure Battalion vs Platoon mode consistency in API responses (Fixed 404 in `form_summary`). <!-- id: 8.2 -->
- [x] **Exports Engine** <!-- id: 9 -->
  - [x] ENFORCE filters on Export endpoints: Require `week` and `platoon` (where applicable). <!-- id: 9.1 -->
  - [x] Implement meaningful error messages (404/422) for empty exports. <!-- id: 9.2 -->
  - [x] Add smoke tests for exporting logic constraints. <!-- id: 9.3 -->
  - [x] Ensure export filenames are dynamic and descriptive (e.g., `Spearhead_Export_Platoon_<x>_<Week>.xlsx`). <!-- id: 9.4 -->

## Phase 4: UX Polish & Consistency

Focus on professional look-and-feel and usability.

- [x] **Dashboard Refinement** <!-- id: 10 -->
  - [x] Unify Filter Bar: Create a single source of truth for Month/Week/Platoon selectors. <!-- id: 10.1 -->
  - [x] Persist user preferences (View Mode, Last Platoon) in `localStorage`. <!-- id: 10.2 -->
  - [x] Standardize Empty States: Use `EmptyCard` consistently across all tables/charts. <!-- id: 10.3 -->
  - [x] RTL Polish: Verify all charts and tables align correctly for Hebrew. <!-- id: 10.4 -->
- [x] **Navigation & Assets** <!-- id: 11 -->
  - [x] Verify Platoon Card Logos match the asset map. <!-- id: 11.1 -->
  - [x] Implement "Skeleton Loading" states for smoother transitions. <!-- id: 11.2 -->

## Phase 5: Operational Readiness

Focus on making the system runnable, debuggable, and maintainable.

- [x] **Environment Stability** <!-- id: 12 -->
  - [x] Create `scripts/setup-venv.sh` with self-healing capabilities. <!-- id: 12.1 -->
  - [x] Create `scripts/dev-one-click.sh` for reliable local startup. <!-- id: 12.2 -->
- [x] **Observability** <!-- id: 13 -->
  - [x] Structured Logging: JSON format with `request_id`, `platoon`, `auth_mode`. <!-- id: 13.1 -->
  - [/] Log Retention/Cleanup Policy. <!-- id: 13.2 -->
- [x] **Documentation** <!-- id: 14 -->
  - [x] Create `operational-runbook.md`: "How to restart", "How to clean DB", "How to debug auth". <!-- id: 14.1 -->
  - [ ] Document Sync Header usage for API consumers. <!-- id: 14.2 -->

## Phase 6: Architecture Hardening & Sterility

Focus on Robustness, Isolation, and functional correctness.

- [ ] **Robust Data Ingestion** <!-- id: 16 -->
  - [ ] Update `FieldMapper.infer_platoon` to ignore suffixes like `(תגובות)`. <!-- id: 16.1 -->
  - [ ] Add explicit regex mapping for known units (Kfir, Lahav, etc.). <!-- id: 16.2 -->
- [ ] **Sterile Authorization** <!-- id: 17 -->
  - [ ] Implement `User` model and `get_current_user` dependency. <!-- id: 17.1 -->
  - [ ] Enforce Tenant Isolation in all routers (403 if platoon != user.platoon). <!-- id: 17.2 -->
- [ ] **Functional Fixes** <!-- id: 18 -->
  - [ ] Verify Export logic works with fixed data. <!-- id: 18.1 -->
  - [ ] Verify "No Data" states are handled gracefully in UI 404s. <!-- id: 18.2 -->
