import shutil
from pathlib import Path

from iron_view.data.import_service import ImportService
from iron_view.sync.google_sheets import SyncService, SheetsProvider


BASE = Path(__file__).resolve().parents[1]


class FakeSheetsProvider:
    def __init__(self, fixture_dir: Path):
        self.fixture_dir = fixture_dir

    def download_sheet(self, file_id: str, dest: Path) -> Path:
        # file_id here is the filename to copy from fixtures
        src = self.fixture_dir / file_id
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        return dest


def test_sync_service(tmp_path):
    db_path = tmp_path / "ironview.db"
    import_service = ImportService(db_path=db_path)

    fixture_dir = BASE / "docs/Files"
    provider = FakeSheetsProvider(fixture_dir)
    file_ids = {
        "platoon_loadout": "דוחות פלוגת כפיר (1).xlsx",
        "battalion_summary": "מסמך דוחות גדודי (1).xlsx",
        "form_responses": "טופס דוחות סמפ כפיר. (תגובות) (1).xlsx",
    }

    sync_service = SyncService(import_service=import_service, provider=provider, file_ids=file_ids)
    result = sync_service.sync_all()

    assert result["platoon_loadout"] > 0
    assert result["form_responses"] > 0

    # Idempotent: second run should insert zero because hashes match
    result2 = sync_service.sync_all()
    assert result2["platoon_loadout"] == 0
