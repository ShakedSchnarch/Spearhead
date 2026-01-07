import shutil
import time
from pathlib import Path
from typing import Optional, Protocol, Tuple

import requests
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account

from iron_view.config import settings
from iron_view.data.import_service import ImportService
from iron_view.exceptions import ConfigError, DataSourceError


class SheetsProvider(Protocol):
    def download_sheet(self, file_id: str, dest: Path, cache_path: Optional[Path] = None) -> Tuple[Path, bool]:
        ...


class GoogleSheetsProvider:
    """
    Downloads Google Sheets as XLSX using either a service account or API key.
    """

    EXPORT_URL = "https://docs.google.com/spreadsheets/d/{file_id}/export"

    def __init__(
        self,
        service_account_file: Optional[Path] = None,
        api_key: Optional[str] = None,
        max_retries: int = 3,
        backoff_seconds: float = 1.0,
    ):
        self.api_key = api_key
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.creds = None
        if service_account_file and Path(service_account_file).exists():
            self.creds = service_account.Credentials.from_service_account_file(
                service_account_file,
                scopes=["https://www.googleapis.com/auth/drive.readonly"],
            )

    def download_sheet(self, file_id: str, dest: Path, cache_path: Optional[Path] = None) -> Tuple[Path, bool]:
        if not file_id:
            raise ConfigError("Google Sheets file_id is not configured.")

        cache_path = Path(cache_path) if cache_path else None
        dest.parent.mkdir(parents=True, exist_ok=True)
        url = self.EXPORT_URL.format(file_id=file_id)
        params = {"format": "xlsx"}

        if self.creds:
            session = AuthorizedSession(self.creds)
            requester = lambda: session.get(url, params=params)
        else:
            if self.api_key:
                params["key"] = self.api_key
            elif not self.api_key:
                raise ConfigError("No credentials or API key configured for Google Sheets.")
            requester = lambda: requests.get(url, params=params)

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                resp = requester()
            except Exception as exc:  # network failure
                last_error = exc
                if attempt < self.max_retries - 1:
                    time.sleep(self.backoff_seconds * (2**attempt))
                    continue
                break

            if resp.status_code == 200:
                dest.write_bytes(resp.content)
                if cache_path:
                    cache_path.parent.mkdir(parents=True, exist_ok=True)
                    cache_path.write_bytes(resp.content)
                return dest, False

            is_retryable = resp.status_code in {429, 500, 502, 503, 504}
            last_error = DataSourceError(f"Failed to download sheet {file_id}: {resp.status_code}")
            if attempt < self.max_retries - 1 and is_retryable:
                time.sleep(self.backoff_seconds * (2**attempt))
                continue
            break

        # Fallback to cache if available
        if cache_path and cache_path.exists():
            shutil.copyfile(cache_path, dest)
            return dest, True

        raise last_error or DataSourceError(f"Failed to download sheet {file_id}")


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

    def sync_platoon_loadout(self) -> int:
        inserted, _ = self._sync("platoon_loadout", self.import_service.import_platoon_loadout)
        return inserted

    def sync_battalion_summary(self) -> int:
        inserted, _ = self._sync("battalion_summary", self.import_service.import_battalion_summary)
        return inserted

    def sync_form_responses(self) -> int:
        inserted, _ = self._sync("form_responses", self.import_service.import_form_responses)
        return inserted

    def sync_all(self) -> dict[str, int]:
        return {
            "platoon_loadout": self.sync_platoon_loadout(),
            "battalion_summary": self.sync_battalion_summary(),
            "form_responses": self.sync_form_responses(),
        }

    def get_status(self) -> dict:
        return {
            "enabled": settings.google.enabled,
            "files": self.status,
        }

    def _sync(self, key: str, import_fn) -> tuple[int, bool]:
        try:
            path, used_cache = self._download(key)
            inserted = import_fn(path)
            self._update_status(key, inserted=inserted, used_cache=used_cache, error=None)
            return inserted, used_cache
        except Exception as exc:
            self._update_status(key, inserted=0, used_cache=False, error=str(exc))
            raise

    def _download(self, key: str) -> Tuple[Path, bool]:
        file_id = self.file_ids.get(key)
        dest = self.tmp_dir / f"{key}.xlsx"
        cache_path = self.cache_dir / f"{key}.xlsx"
        try:
            return self.provider.download_sheet(file_id, dest, cache_path=cache_path)
        except Exception:
            if cache_path.exists():
                shutil.copyfile(cache_path, dest)
                return dest, True
            raise

    def _update_status(self, key: str, inserted: int, used_cache: bool, error: Optional[str]):
        self.status[key] = {
            "last_sync": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "inserted": inserted,
            "used_cache": used_cache,
            "status": "error" if error else "ok",
        }
        if error:
            self.status[key]["error"] = error
