import time
import shutil
from pathlib import Path
from typing import Optional

from spearhead.config import settings
from spearhead.data.import_service import ImportService
from spearhead.exceptions import ConfigError
from spearhead.sync.provider import SheetsProvider

# Re-export SheetsProvider for backward compatibility if needed, though better to import from provider.py.
# But SyncService uses it.

class SyncService:
    """
    Syncs configured Google Sheets into the local import pipeline.
    """

    def __init__(
        self,
        import_service: ImportService,
        provider: SheetsProvider,
        file_ids: dict[str, str],
        cache_dir: Optional[Path] = None,
    ):
        self.import_service = import_service
        self.provider = provider
        self.file_ids = file_ids
        self.tmp_dir = Path(settings.paths.input_dir) / "sync_tmp"
        self.cache_dir = Path(cache_dir) if cache_dir else Path(settings.google.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.status: dict[str, dict] = {}

    def sync_platoon_loadout(self, user_token: Optional[str] = None) -> int:
        inserted, _ = self._sync("platoon_loadout", self.import_service.import_platoon_loadout, user_token=user_token)
        return inserted

    def sync_battalion_summary(self, user_token: Optional[str] = None) -> int:
        inserted, _ = self._sync("battalion_summary", self.import_service.import_battalion_summary, user_token=user_token)
        return inserted

    def sync_form_responses(self, user_token: Optional[str] = None) -> int:
        ids_config = self.file_ids.get("form_responses", {})
        
        # Normalize to dict[platoon_alias, file_id]
        targets: dict[str, str] = {}
        if isinstance(ids_config, str):
            import json
            try:
                if ids_config.strip().startswith("{"):
                    ids_config = json.loads(ids_config)
                    # Fallthrough to dict handler
            except Exception:
                pass

        if isinstance(ids_config, str):
            targets = {"unknown": ids_config}
        elif isinstance(ids_config, list):
             targets = {f"unknown_{i}": fid for i, fid in enumerate(ids_config)}
        elif isinstance(ids_config, dict):
            targets = ids_config
            
        total_inserted = 0
        overall_status = "ok"
        errors = []

        for platoon_alias, fid in targets.items():
            # Use platoon alias in key for status tracking
            key = f"form_responses_{platoon_alias}"
            # Ensure _download can find the ID
            self.file_ids[key] = fid 
            
            try:
                # If alias looks like a real name (not unknown_X), assume it is the platoon name
                platoon_override = platoon_alias if not platoon_alias.startswith("unknown") else None
                
                inserted, _ = self._sync(
                    key,
                    lambda path: self.import_service.import_form_responses(
                        path, source_id=fid, platoon=platoon_override
                    ),
                    user_token=user_token,
                )
                total_inserted += inserted
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Failed to sync {key} (ID: {fid}): {e}")
                overall_status = "partial_error"
                errors.append(str(e))
        
        return total_inserted

    def sync_all(self, user_token: Optional[str] = None) -> dict[str, int]:
        return {
            "platoon_loadout": self.sync_platoon_loadout(user_token=user_token),
            "battalion_summary": self.sync_battalion_summary(user_token=user_token),
            "form_responses": self.sync_form_responses(user_token=user_token),
        }

    def get_status(self) -> dict:
        return {
            "enabled": settings.google.enabled,
            "files": self.status,
        }

    def _sync(self, key: str, import_fn, user_token: Optional[str] = None) -> tuple[int, bool]:
        try:
            path, used_cache, etag, auth_mode = self._download(key, user_token=user_token)
            import zipfile
            try:
                inserted = import_fn(path)
            except zipfile.BadZipFile:
                # Corrupted file, likely a partial download or non-Excel file.
                # Invalidate cache if we used it, or just report error.
                if used_cache:
                     # If cache was bad, maybe delete it?
                     pass
                raise  # Re-raise to be caught by the outer loop and logged as error
            self._update_status(
                key,
                inserted=inserted,
                used_cache=used_cache,
                etag=etag,
                error=None,
                auth_mode=auth_mode,
            )
            return inserted, used_cache
        except Exception as exc: # Catching generic Exception includes ConfigError if imported or defined
             # But wait, ConfigError is from spearhead.exceptions.
             # Let's import it.
             from spearhead.exceptions import ConfigError
             if isinstance(exc, ConfigError):
                # Missing configuration: mark as skipped
                self._update_status(
                    key,
                    inserted=0,
                    used_cache=False,
                    etag=None,
                    error=str(exc),
                    status="skipped",
                    auth_mode=None,
                )
                return 0, False
             
             self._update_status(key, inserted=0, used_cache=False, etag=None, error=str(exc), auth_mode=None)
             raise

    def _download(self, key: str, user_token: Optional[str] = None) -> tuple[Path, bool, Optional[str], Optional[str]]:
        from spearhead.exceptions import ConfigError
        file_id = self.file_ids.get(key)
        if not file_id:
            raise ConfigError(f"Google Sheets file_id is not configured for '{key}'.")
        dest = self.tmp_dir / f"{key}.xlsx"
        cache_path = self.cache_dir / f"{key}.xlsx"
        etag = self.status.get(key, {}).get("etag")
        try:
            path, used_cache, new_etag, auth_mode = self.provider.download_sheet(
                file_id, dest, cache_path=cache_path, etag=etag, user_token=user_token
            )
            if new_etag:
                self.status.setdefault(key, {})["etag"] = new_etag
            return path, used_cache, new_etag or etag, auth_mode
        except Exception:
            if cache_path.exists():
                shutil.copyfile(cache_path, dest)
                return dest, True, etag, "cache"
            raise

    def _update_status(
        self,
        key: str,
        inserted: int,
        used_cache: bool,
        etag: Optional[str],
        error: Optional[str],
        status: str = "ok",
        auth_mode: Optional[str] = None,
    ):
        existing_etag = etag or self.status.get(key, {}).get("etag")
        status_value = status or ("error" if error else "ok")
        self.status[key] = {
            "last_sync": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "inserted": inserted,
            "used_cache": used_cache,
            "status": status_value if not error else status_value,
            "source": "cache" if used_cache else "remote",
        }
        if existing_etag:
            self.status[key]["etag"] = existing_etag
        if auth_mode:
            self.status[key]["auth_mode"] = auth_mode
        if error:
            self.status[key]["error"] = error
        try:
            schema = self.import_service.db.latest_schema_snapshot(source_type=key)
            if schema:
                self.status[key]["schema"] = schema
        except Exception:
            pass
