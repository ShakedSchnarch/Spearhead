from hashlib import md5
import json
import logging
from pathlib import Path
from typing import Iterable, Optional

from spearhead.data.adapters import (
    PlatoonLoadoutAdapter,
    BattalionSummaryAdapter,
    FormResponsesAdapter,
)
from spearhead.data.dto import TabularRecord, FormResponseRow
from spearhead.data.storage import Database
from spearhead.config import settings
from spearhead.data.field_mapper import SchemaSnapshot

logger = logging.getLogger(__name__)


class ImportService:
    """
    Ingests source files (local for now) into the SQLite store.
    Idempotent per (import_key) derived from source type + file hash.
    """

    def __init__(self, db_path: Optional[Path] = None):
        db_path = db_path or settings.paths.db_path
        self.db = Database(db_path)
        self._schema_dir = Path(settings.paths.input_dir) / "schema_snapshots"

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

    def import_form_responses(self, file_path: Path, source_id: Optional[str] = None, platoon: Optional[str] = None) -> int:
        responses, schema = FormResponsesAdapter.load_with_schema(file_path, source_id=source_id, platoon=platoon)
        import_id, is_new = self._register_import(file_path, settings.imports.form_responses_label)
        # if not is_new:
        #     return 0
        logger.info(f"DEBUG: Inserting {len(responses)} records into DB (import_id={import_id})")
        inserted = self.db.insert_form_responses(import_id, responses)
        if schema:
            self._store_schema_snapshot(import_id, settings.imports.form_responses_label, schema)
        return inserted

    def _register_import(self, file_path: Path, source_type: str) -> tuple[int, bool]:
        file_hash = self._hash_file(file_path)
        import_key = f"{source_type}:{file_hash}"
        return self.db.upsert_import(import_key, file_path, source_type)

    def _store_schema_snapshot(self, import_id: int, source_type: str, snapshot: SchemaSnapshot) -> None:
        payload = snapshot.to_dict()
        payload["import_id"] = import_id
        payload["source_type"] = source_type
        try:
            self.db.insert_schema_snapshot(import_id, source_type, payload)
        except Exception:
            logging.getLogger(__name__).exception(
                "failed to persist schema snapshot to db",
                extra={"import_id": import_id, "source_type": source_type},
            )
        try:
            self._schema_dir.mkdir(parents=True, exist_ok=True)
            sidecar = self._schema_dir / f"{import_id}_{source_type}.json"
            sidecar.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            logging.getLogger(__name__).exception(
                "failed to write schema sidecar",
                extra={"import_id": import_id, "source_type": source_type, "path": str(self._schema_dir)},
            )

    @staticmethod
    def _hash_file(file_path: Path) -> str:
        h = md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
