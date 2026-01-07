#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DB_PATH="$ROOT/data/ironview.db"

echo "Resetting database at $DB_PATH"
rm -f "$DB_PATH"

# Activate venv if present
if [[ -z "${VIRTUAL_ENV:-}" && -x "$ROOT/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
fi

export PYTHONPATH="$ROOT/src"

python - <<'PY'
from pathlib import Path

from iron_view.data.import_service import ImportService
from iron_view.services.analytics import FormAnalytics
from iron_view.services.exporter import ExcelExporter

root = Path(__file__).resolve().parents[1]
sample_dir = root / "docs" / "Files"

svc = ImportService()

sources = {
    "platoon_loadout": sample_dir / "דוחות פלוגת כפיר.xlsx",
    "battalion_summary": sample_dir / "מסמך דוחות גדודי.xlsx",
    "form_responses": sample_dir / "טופס דוחות סמפ כפיר. (תגובות).xlsx",
}

for key, path in sources.items():
    if not path.exists():
        print(f"Skipping {key}: {path} not found")
        continue
    importer = getattr(svc, f"import_{key}")
    inserted = importer(path)
    print(f"Imported {inserted} rows from {path.name}")

analytics = FormAnalytics(svc.db)
week = analytics.latest_week()
if not week:
    print("No week data found in form responses; exports skipped.")
else:
    exporter = ExcelExporter(analytics)
    paths = exporter.export_all_for_week(week=week)
    for label, output in paths.items():
        print(f"Wrote {label} report -> {output}")

PY
