from hashlib import md5
from pathlib import Path
from typing import Iterable, Optional

from iron_view.data.adapters import (
    PlatoonLoadoutAdapter,
    BattalionSummaryAdapter,
    FormResponsesAdapter,
)
from iron_view.data.dto import TabularRecord, FormResponseRow
from iron_view.data.storage import Database
from iron_view.config import settings


class ImportService:
    """
    Ingests source files (local for now) into the SQLite store.
    Idempotent per (import_key) derived from source type + file hash.
    """

    def __init__(self, db_path: Optional[Path] = None):
        db_path = db_path or settings.paths.db_path
        self.db = Database(db_path)

    def import_platoon_loadout(self, file_path: Path) -> int:
        records = PlatoonLoadoutAdapter.load(file_path)
        import_id, is_new = self._register_import(file_path, settings.imports.platoon_loadout_label)
        if not is_new:
            return 0
        return self.db.insert_tabular_records(import_id, records)

    def import_battalion_summary(self, file_path: Path) -> int:
        records = BattalionSummaryAdapter.load(file_path)
        import_id, is_new = self._register_import(file_path, settings.imports.battalion_summary_label)
        if not is_new:
            return 0
        return self.db.insert_tabular_records(import_id, records)

    def import_form_responses(self, file_path: Path) -> int:
        responses = FormResponsesAdapter.load(file_path)
        import_id, is_new = self._register_import(file_path, settings.imports.form_responses_label)
        if not is_new:
            return 0
        return self.db.insert_form_responses(import_id, responses)

    def _register_import(self, file_path: Path, source_type: str) -> tuple[int, bool]:
        file_hash = self._hash_file(file_path)
        import_key = f"{source_type}:{file_hash}"
        return self.db.upsert_import(import_key, file_path, source_type)

    @staticmethod
    def _hash_file(file_path: Path) -> str:
        h = md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
