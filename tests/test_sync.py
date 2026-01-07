import shutil
from pathlib import Path

from iron_view.data.import_service import ImportService
from iron_view.exceptions import DataSourceError
from iron_view.sync.google_sheets import SyncService, SheetsProvider


BASE = Path(__file__).resolve().parents[1]


class FakeSheetsProvider:
    def __init__(self, fixture_dir: Path):
        self.fixture_dir = fixture_dir

    def download_sheet(self, file_id: str, dest: Path, cache_path: Path | None = None, etag: str | None = None):
        # file_id here is the filename to copy from fixtures
        src = self.fixture_dir / file_id
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        if cache_path:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, cache_path)
        return dest, False, "fake-etag"


def test_sync_service(tmp_path):
    db_path = tmp_path / "ironview.db"
    import_service = ImportService(db_path=db_path)

    fixture_dir = BASE / "docs/Files"
    provider = FakeSheetsProvider(fixture_dir)
    file_ids = {
        "platoon_loadout": "דוחות פלוגת כפיר.xlsx",
        "battalion_summary": "מסמך דוחות גדודי.xlsx",
        "form_responses": "טופס דוחות סמפ כפיר. (תגובות).xlsx",
    }

    sync_service = SyncService(import_service=import_service, provider=provider, file_ids=file_ids)
    result = sync_service.sync_all()

    assert result["platoon_loadout"] > 0
    assert result["form_responses"] > 0
    status = sync_service.get_status()
    assert status["files"]["form_responses"]["schema"]["raw_headers"]

    # Idempotent: second run should insert zero because hashes match
    result2 = sync_service.sync_all()
    assert result2["platoon_loadout"] == 0
    assert result2["form_responses"] == 0


class FlakyProvider:
    """
    Fails once, then succeeds; used to validate retry/backoff and status tracking.
    """

    def __init__(self, fixture_dir: Path):
        self.fixture_dir = fixture_dir
        self.calls = 0

    def download_sheet(self, file_id: str, dest: Path, cache_path: Path | None = None, etag: str | None = None):
        self.calls += 1
        if self.calls == 1:
            raise DataSourceError("transient error")
        src = self.fixture_dir / file_id
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        if cache_path:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, cache_path)
        return dest, False, "flaky-etag"


def test_sync_status_and_cache_fallback(tmp_path, monkeypatch):
    db_path = tmp_path / "ironview.db"
    import_service = ImportService(db_path=db_path)
    fixture_dir = BASE / "docs/Files"

    # Prepare cache so fallback works when provider fails.
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached_src = fixture_dir / "דוחות פלוגת כפיר.xlsx"
    cached_target = cache_dir / "platoon_loadout.xlsx"
    shutil.copyfile(cached_src, cached_target)

    class AlwaysFailProvider:
        def download_sheet(self, file_id: str, dest: Path, cache_path: Path | None = None, etag: str | None = None):
            raise DataSourceError("network down")

    provider = AlwaysFailProvider()
    file_ids = {
        "platoon_loadout": "דוחות פלוגת כפיר.xlsx",
        "battalion_summary": "מסמך דוחות גדודי.xlsx",
        "form_responses": "טופס דוחות סמפ כפיר. (תגובות).xlsx",
    }

    sync_service = SyncService(
        import_service=import_service,
        provider=provider,
        file_ids=file_ids,
        cache_dir=cache_dir,
    )

    inserted = sync_service.sync_platoon_loadout()
    assert inserted > 0

    status = sync_service.get_status()
    assert status["files"]["platoon_loadout"]["status"] == "ok"
    assert status["files"]["platoon_loadout"]["used_cache"] is True
    assert "etag" not in status["files"]["platoon_loadout"]  # no etag in fallback scenario


def test_google_provider_retries_and_uses_cache(tmp_path, monkeypatch):
    """
    Validate retry/backoff path and cache fallback inside GoogleSheetsProvider.
    """
    from iron_view.sync.google_sheets import GoogleSheetsProvider
    calls = {"count": 0}

    class FakeResp:
        def __init__(self, status_code: int, content: bytes = b"", etag: str | None = None):
            self.status_code = status_code
            self.content = content
            self.headers = {}
            if etag:
                self.headers["ETag"] = etag

    def fake_get(url, params=None, headers=None):
        calls["count"] += 1
        if calls["count"] == 1:
            return FakeResp(500)
        if calls["count"] == 2:
            return FakeResp(200, b"data", etag="etag1")
        return FakeResp(200, b"data2", etag="etag2")

    monkeypatch.setattr("iron_view.sync.google_sheets.requests.get", fake_get)
    provider = GoogleSheetsProvider(api_key="fake", max_retries=3, backoff_seconds=0)
    dest = tmp_path / "out.xlsx"
    cache_path = tmp_path / "cache.xlsx"

    path, used_cache, etag = provider.download_sheet("file123", dest, cache_path=cache_path)
    assert path.exists()
    assert used_cache is False
    assert etag == "etag1"
    assert calls["count"] == 2  # retried once after failure
    _, _, _ = provider.download_sheet("file123", dest, cache_path=cache_path, etag="etag123")


def test_sync_service_etag_tracked(tmp_path):
    db_path = tmp_path / "ironview.db"
    import_service = ImportService(db_path=db_path)
    fixture_dir = BASE / "docs/Files"

    class EtagProvider:
        def __init__(self, fixture_dir: Path):
            self.fixture_dir = fixture_dir
            self.called_etag = None

        def download_sheet(self, file_id: str, dest: Path, cache_path: Path | None = None, etag: str | None = None):
            self.called_etag = etag
            src = self.fixture_dir / file_id
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
            if cache_path:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, cache_path)
            return dest, False, "etag-value"

    provider = EtagProvider(fixture_dir)
    file_ids = {
        "platoon_loadout": "דוחות פלוגת כפיר.xlsx",
        "battalion_summary": "מסמך דוחות גדודי.xlsx",
        "form_responses": "טופס דוחות סמפ כפיר. (תגובות).xlsx",
    }

    sync_service = SyncService(import_service=import_service, provider=provider, file_ids=file_ids)
    sync_service.sync_platoon_loadout()
    status = sync_service.get_status()
    assert status["files"]["platoon_loadout"]["etag"] == "etag-value"
