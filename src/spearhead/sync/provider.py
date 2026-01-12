import shutil
import time
from pathlib import Path
from typing import Optional, Protocol, Tuple

import requests
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials

from spearhead.exceptions import ConfigError, DataSourceError

class SheetsProvider(Protocol):
    def download_sheet(
        self,
        file_id: str,
        dest: Path,
        cache_path: Optional[Path] = None,
        etag: Optional[str] = None,
        user_token: Optional[str] = None,
    ) -> Tuple[Path, bool, Optional[str], str]:
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

    def download_sheet(
        self,
        file_id: str,
        dest: Path,
        cache_path: Optional[Path] = None,
        etag: Optional[str] = None,
        user_token: Optional[str] = None,
    ) -> Tuple[Path, bool, Optional[str], str]:
        if not file_id:
            raise ConfigError("Google Sheets file_id is not configured.")

        cache_path = Path(cache_path) if cache_path else None
        dest.parent.mkdir(parents=True, exist_ok=True)
        url = self.EXPORT_URL.format(file_id=file_id)
        params = {"format": "xlsx"}
        headers = {}
        if etag:
            headers["If-None-Match"] = etag

        requesters: list[tuple[str, callable]] = []

        if user_token:
            user_creds = Credentials(token=user_token)
            user_session = AuthorizedSession(user_creds)
            requesters.append(("user", lambda: user_session.get(url, params=params, headers=headers)))

        if self.creds:
            sa_session = AuthorizedSession(self.creds)
            requesters.append(("service_account", lambda: sa_session.get(url, params=params, headers=headers)))
        else:
            if self.api_key:
                params["key"] = self.api_key
            requesters.append(("api_key", lambda: requests.get(url, params=params, headers=headers)))

        if not requesters:
            raise ConfigError("No credentials or API key configured for Google Sheets.")

        last_error: Optional[Exception] = None
        new_etag: Optional[str] = None
        for requester_name, requester in requesters:
            for attempt in range(self.max_retries):
                try:
                    resp = requester()
                except Exception as exc:  # network failure
                    last_error = exc
                    if attempt < self.max_retries - 1:
                        time.sleep(self.backoff_seconds * (2**attempt))
                        continue
                    break

                if resp.status_code == 304 and cache_path and cache_path.exists():
                    shutil.copyfile(cache_path, dest)
                    return dest, True, etag, requester_name

                if resp.status_code == 200:
                    new_etag = resp.headers.get("ETag")
                    dest.write_bytes(resp.content)
                    if cache_path:
                        cache_path.parent.mkdir(parents=True, exist_ok=True)
                        cache_path.write_bytes(resp.content)
                    return dest, False, new_etag, requester_name

                is_retryable = resp.status_code in {429, 500, 502, 503, 504}
                should_fallback = resp.status_code in {401, 403}
                last_error = DataSourceError(f"Failed to download sheet {file_id}: {resp.status_code}")
                if attempt < self.max_retries - 1 and is_retryable:
                    time.sleep(self.backoff_seconds * (2**attempt))
                    continue
                if should_fallback:
                    break  # try next requester (service account/api key)
                break

        # Fallback to cache if available
        if cache_path and cache_path.exists():
            shutil.copyfile(cache_path, dest)
            return dest, True, etag, "cache"

        raise last_error or DataSourceError(f"Failed to download sheet {file_id}")
