from pathlib import Path
import pytest
from spearhead.data.import_service import ImportService
from spearhead.data.repositories import FormRepository
from spearhead.services.analytics import FormAnalytics

BASE = Path(__file__).resolve().parents[1]
# Use the file provided by the user, assuming it exists
FORM_FILE = BASE / "docs/Files/טופס דוחות סמפ כפיר. (תגובות).xlsx"

@pytest.fixture
def bootstrap_service(tmp_path):
    """
    Bootstrap a fresh database with imported form responses.
    """
    db_path = tmp_path / "spearhead.db"
    svc = ImportService(db_path=db_path)
    if FORM_FILE.exists():
        svc.import_form_responses(FORM_FILE)
    return svc

@pytest.fixture
def form_repo(bootstrap_service):
    return FormRepository(bootstrap_service.db)

@pytest.fixture
def analytics(form_repo):
    return FormAnalytics(form_repo)
