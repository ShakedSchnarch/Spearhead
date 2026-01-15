#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Resolve DB path from settings (fallback if config not ready)
DB_PATH="$("$ROOT/.venv/bin/python" - <<'PY' 2>/dev/null || echo "$ROOT/data/spearhead.db"
from spearhead.config import settings
print((settings.paths.db_path).resolve())
PY
)"

echo "Resetting database at $DB_PATH"
rm -f "$DB_PATH"

# Activate venv if present
if [[ -z "${VIRTUAL_ENV:-}" && -x "$ROOT/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
fi

PYTHON_BIN="$ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

export PYTHONPATH="$ROOT/src"

"$PYTHON_BIN" - <<'PY'
from pathlib import Path

from spearhead.data.import_service import ImportService
from spearhead.services.analytics import FormAnalytics
from spearhead.services.exporter import ExcelExporter
from spearhead.services.intelligence import IntelligenceService
from spearhead.logic.scoring import ScoringEngine
from spearhead.data.repositories import FormRepository

root = Path.cwd()
sample_dir = root / "docs" / "Files"
legacy_dir = sample_dir / "Old_Files_To_Learn_from"

svc = ImportService()

def resolve(path: Path) -> Path | None:
    if path.exists():
        return path
    candidate = legacy_dir / path.name
    return candidate if candidate.exists() else None

sources = {
    "platoon_loadout": resolve(sample_dir / "דוחות פלוגת כפיר.xlsx"),
    "battalion_summary": resolve(sample_dir / "מסמך דוחות גדודי.xlsx"),
    "form_responses": resolve(sample_dir / "טופס דוחות סמפ כפיר. (תגובות).xlsx"),
}

for key, path in sources.items():
    if not path:
        print(f"Skipping {key}: sample not found")
        continue
    importer = getattr(svc, f"import_{key}")
    inserted = importer(path)
    print(f"Imported {inserted} rows from {path.name}")

repo = FormRepository(svc.db)
analytics = FormAnalytics(repo)
week = analytics.latest_week()
if not week:
    print("No week data found in form responses; exports skipped.")
else:
    intel = IntelligenceService(repository=repo, scoring_engine=ScoringEngine())
    exporter = ExcelExporter(analytics=analytics, intelligence=intel)
    paths = exporter.export_all_for_week(week=week)
    for label, output in paths.items():
        print(f"Wrote {label} report -> {output}")

PY
