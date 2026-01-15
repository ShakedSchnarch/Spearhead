# Fix Platoon Data Synchronization and Display Issues

The user is experiencing issues with missing components and synchronized data in the platoon and battalion views. The specific error found is a `403 Forbidden` response when the frontend attempts to fetch `/queries/forms/coverage` for a platoon-restricted user. Additional issues may exist in the frontend preventing data from being displayed even if the API call succeeds.

## Proposed Changes

### Backend

1.  **Modify `src/spearhead/services/analytics.py`**:

    - Update the `coverage` method to accept an optional `platoon` argument.
    - If `platoon` is provided, filter the `df` or processing logic to only include data for that platoon.
    - Ensure the returned structure is consistent with what the frontend expects, even for a single platoon.
    - **New**: Sanitize the `week` argument in `coverage`, `summarize`, and `get_gaps` to strip potential corrupted characters (e.g. `%D6%BF`) from the frontend.

2.  **Modify `src/spearhead/api/routers/queries.py`**:
    - Update the `form_coverage` endpoint.
    - Remove the `403 Forbidden` raise for restricted users.
    - Instead, if `user.platoon` is set, pass it as the `platoon` argument to `analytics.coverage`.

### Frontend

1.  **Modify `frontend-app/src/hooks/useDashboardData.js`**:
    - Update the `coverage` query definition.
    - Remove the `!isRestricted` condition from the `enabled` flag.
    - Ensure the query passes the correct parameters.

## Current Status & Next Steps

### Architecture Update

- **Internal Logic**: The backend now strictly enforces English keys internally (e.g., "Kfir").
- **Data Ingestion**: The database contains _both_ Hebrew ("כפיר") and English ("Kfir") labels due to legacy imports.
- **Filtering**: `BaseRepository.apply_scope` has been patched to perform "Reverse Alias Lookup", capturing rows in any language that map to the requested English key.

### Outstanding Issues

1.  **Corrupted Week Parameter**: The frontend is sending `%D6%BF` (Rafe) characters in the week parameter (`%D6%BF2026-W01`). Backend sanitization exists but might be bypassed or insufficient if the variable persists in frontend state.
2.  **Display Gaps**: User reports specific UI components (likely query-based tables) are not showing data, potentially due to the same parameter corruption or missing API endpoints for specific views.
3.  **Local Files**: Data from local Excel files (not Google Sheets) is reported as "incorrect". This suggests the `ImportService` might need stricter validation or normalization during ingestion.

### Verification Plan (Next Session)

#### Backend

- [ ] Debug `ImportService` to ensure local file ingestion normalizes platoon names _before_ saving to DB.
- [ ] Strengthen `FormAnalytics._sanitize_week` to aggressively strip non-ASCII/numeric characters at the API entry point.

#### Frontend

- [ ] Audit `DashboardContent.jsx` to ensure it requests the correct API endpoints for "local file" data.
- [ ] Clear browser storage/cache to remove persisting `%D6%BF` week values.

#### Tests

- [ ] Improve test coverage for `ImportService` with mixed Hebrew/English input files.
