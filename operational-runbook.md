# Operational Runbook

## 1. Quick Start (Dev)

To start the full environment (DB + Backend + Frontend):

```bash
./scripts/dev-one-click.sh
```

To reset the database (DANGER: Deletes all data!):

```bash
./scripts/dev-one-click.sh --reset-db
```

## 2. Logs & Debugging

Logs are output to the console.

- **Console Mode (Default)**: Human-readable logs.
- **JSON Mode**: Set `LOGGING__FORMAT=json` for machine-readable logs with `request_id`, `path`, `status`.

Example tracing a request:

1. Trigger the error.
2. Search logs for the `request_id` from the error response or headers.
3. Observe `duration_ms` and `status`.

## 3. Environment Troubleshooting

**Issue**: `ImportError` or `ModuleNotFoundError` despite packages being installed.
**Cause**: Virtual environment corruption (e.g., `importlib` freeze).
**Fix**: Run setup script to self-heal.

```bash
./scripts/setup-venv.sh
```

**Issue**: Frontend assets not updating.
**Fix**: Rebuild the UI.

```bash
./scripts/build-ui.sh
```

## 4. Auth Modes

The system supports two auth modes (configured in `.env` or `config/settings.yaml`):

1. **No Auth**: `security.require_auth_on_queries = false` (Default for dev).
2. **Basic Auth**: Set `SECURITY__BASIC_USER` and `SECURITY__BASIC_PASS`.
3. **Token Auth**: Set `SECURITY__API_TOKEN`.

## 5. Sync Integration

- The system syncs from Google Sheets or Excel files in `docs/Files`.
- Run manual sync via:

```bash
./scripts/sync-and-export.sh
```
