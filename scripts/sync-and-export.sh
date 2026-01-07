#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Activate venv if present (even if activate is not executable)
if [[ -z "${VIRTUAL_ENV:-}" && -f "$ROOT/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
fi

export PYTHONPATH="$ROOT/src"

python - <<'PY'
from pathlib import Path
import sys
from iron_view.config import settings
from iron_view.data.import_service import ImportService
from iron_view.sync.google_sheets import GoogleSheetsProvider, SyncService
from iron_view.services.analytics import FormAnalytics
from iron_view.services.exporter import ExcelExporter

root = Path.cwd()

db_path = settings.paths.db_path

print(f"Resetting DB at {db_path}")
db_path.parent.mkdir(parents=True, exist_ok=True)
if db_path.exists():
    db_path.unlink()

svc = ImportService(db_path=db_path)

inserted = {}
if settings.google.enabled:
    print("Google sync enabled — downloading and importing...")
    provider = GoogleSheetsProvider(
        service_account_file=settings.google.service_account_file,
        api_key=settings.google.api_key,
        max_retries=settings.google.max_retries,
        backoff_seconds=settings.google.backoff_seconds,
    )
    sync = SyncService(
        import_service=svc,
        provider=provider,
        file_ids=settings.google.file_ids,
        cache_dir=settings.google.cache_dir,
    )
    inserted = sync.sync_all()
else:
    print("Google sync disabled. Falling back to local sample files in docs/Files/")
    sample_dir = root / "docs" / "Files"
    sources = {
        "platoon_loadout": sample_dir / "דוחות פלוגת כפיר.xlsx",
        "battalion_summary": sample_dir / "מסמך דוחות גדודי.xlsx",
        "form_responses": sample_dir / "טופס דוחות סמפ כפיר. (תגובות).xlsx",
    }
    for key, path in sources.items():
        if not path.exists():
            print(f"[warn] Skipping {key}: {path} not found")
            continue
        importer = getattr(svc, f"import_{key}")
        inserted[key] = importer(path)
        print(f"Imported {inserted[key]} rows from {path.name}")

print("Insert summary:", inserted)

analytics = FormAnalytics(svc.db)
week = analytics.latest_week()
if not week:
    print("No form responses available; skipping exports.")
    sys.exit(0)

exporter = ExcelExporter(analytics)
paths = exporter.export_all_for_week(week=week)
for label, outpath in paths.items():
    print(f"Wrote {label} report -> {outpath}")
PY
