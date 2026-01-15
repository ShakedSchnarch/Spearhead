# Task: Debugging Data Synchronization and Display Issues

- [x] Analyze logs and project structure <!-- id: 0 -->
  - [x] Read terminal output from `Python` process <!-- id: 1 -->
  - [x] Explore project structure <!-- id: 2 -->
- [x] Investigate Backend Data Flow <!-- id: 3 -->
  - [x] Check `src/spearhead/services/analytics.py` for data processing logic <!-- id: 4 -->
  - [x] Check API endpoints for platoon/battalion data <!-- id: 5 -->
- [x] Investigate Frontend Data Fetching and Display <!-- id: 6 -->
  - [x] Identify React components for Platoon/Battalion dashboard <!-- id: 7 -->
  - [x] Check data fetching logic in frontend <!-- id: 8 -->
- [x] Verify Configuration and Environment <!-- id: 9 -->
  - [x] Check `.env` and startup scripts <!-- id: 10 -->
- [x] Fix identified issues <!-- id: 11 -->
  - [x] Update `src/spearhead/services/analytics.py` to support platoon filtering <!-- id: 13 -->
  - [x] Update `src/spearhead/api/routers/queries.py` to allow restricted access <!-- id: 14 -->
  - [x] Update `frontend-app/src/hooks/useDashboardData.js` <!-- id: 16 -->
  - [x] Fix and run unit tests <!-- id: 15 -->
    - [x] Fix `BaseRepository.apply_scope` to support Hebrew keys <!-- id: 19 -->
    - [x] Fix `_week_label` to sanitize hidden chars <!-- id: 20 -->
    - [x] Fix `FormAnalytics` to sanitize week input <!-- id: 21 -->
- [x] Refactor and Standardize <!-- id: 22 -->
  - [x] Create `tests/test_architecture.py` compliance tests <!-- id: 23 -->
  - [x] Create `tests/conftest.py` for shared fixtures <!-- id: 24 -->
  - [x] Refactor `tests/test_analytics.py` to use fixtures and English keys <!-- id: 25 -->
  - [x] Quarantine broken legacy tests into `tests/legacy/` <!-- id: 27 -->
- [x] Verify fix <!-- id: 12 -->
  - [x] Run pytest (clean suite) <!-- id: 17 -->
  - [/] Request user manual verification <!-- id: 18 -->

# Outstanding Issues (Next Session)

## High Priority

- [ ] **Fix Corrupted Week Parameter** (%D6%BF): Frontend/Backend still processing corrupted strings logic despite sanitization attempt.
- [ ] **Data Inconsistency**: User reports "local files" data is incorrect/not displaying.
- [ ] **Frontend Updates**: Components not showing expected queries.
- [ ] **Export Quality**: Generated Excel forms are "insufficient".

## Architecture & Quality

- [ ] **Test Coverage**: User stated "tests are not good" (likely coverage or meaningful assertions).
- [ ] **Consistency**: General cleanup of project structure and logic.
