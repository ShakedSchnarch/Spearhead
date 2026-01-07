from pathlib import Path
from typing import Optional, Protocol

import requests
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account

from iron_view.config import settings
from iron_view.data.import_service import ImportService
from iron_view.exceptions import ConfigError, DataSourceError


class SheetsProvider(Protocol):
    def download_sheet(self, file_id: str, dest: Path) -> Path:
        ...


class GoogleSheetsProvider:
    """
    Downloads Google Sheets as XLSX using either a service account or API key.
    """

    EXPORT_URL = "https://docs.google.com/spreadsheets/d/{file_id}/export"

    def __init__(self, service_account_file: Optional[Path] = None, api_key: Optional[str] = None):
        self.api_key = api_key
        self.creds = None
        if service_account_file and Path(service_account_file).exists():
            self.creds = service_account.Credentials.from_service_account_file(
                service_account_file,
                scopes=["https://www.googleapis.com/auth/drive.readonly"],
            )

    def download_sheet(self, file_id: str, dest: Path) -> Path:
        if not file_id:
            raise ConfigError("Google Sheets file_id is not configured.")

        dest.parent.mkdir(parents=True, exist_ok=True)
        url = self.EXPORT_URL.format(file_id=file_id)
        params = {"format": "xlsx"}

        if self.creds:
            session = AuthorizedSession(self.creds)
            resp = session.get(url, params=params)
        elif self.api_key:
            params["key"] = self.api_key
            resp = requests.get(url, params=params)
        else:
            raise ConfigError("No credentials or API key configured for Google Sheets.")

        if resp.status_code != 200:
            raise DataSourceError(f"Failed to download sheet {file_id}: {resp.status_code}")

        dest.write_bytes(resp.content)
        return dest


class SyncService:
    """
    Syncs configured Google Sheets into the local import pipeline.
    """

    def __init__(self, import_service: ImportService, provider: SheetsProvider, file_ids: dict[str, str]):
        self.import_service = import_service
        self.provider = provider
        self.file_ids = file_ids
        self.tmp_dir = Path(settings.paths.input_dir) / "sync_tmp"

    def sync_platoon_loadout(self) -> int:
        path = self._download("platoon_loadout")
        return self.import_service.import_platoon_loadout(path)

    def sync_battalion_summary(self) -> int:
        path = self._download("battalion_summary")
        return self.import_service.import_battalion_summary(path)

    def sync_form_responses(self) -> int:
        path = self._download("form_responses")
        return self.import_service.import_form_responses(path)

    def sync_all(self) -> dict[str, int]:
        return {
            "platoon_loadout": self.sync_platoon_loadout(),
            "battalion_summary": self.sync_battalion_summary(),
            "form_responses": self.sync_form_responses(),
        }

    def _download(self, key: str) -> Path:
        file_id = self.file_ids.get(key)
        dest = self.tmp_dir / f"{key}.xlsx"
        return self.provider.download_sheet(file_id, dest)
