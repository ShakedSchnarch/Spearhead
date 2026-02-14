from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
import yaml

class AppSettings(BaseSettings):
    name: str = "Spearhead"
    version: str = "1.0.0"
    theme: str = "tactical_flat.css"  # Default theme
    enable_legacy_routes: bool = False

class PathSettings(BaseSettings):
    input_dir: Path = Path("./data/input")
    output_dir: Path = Path("./reports")
    templates_dir: Path = Path("./templates")
    assets_dir: Path = Path("./assets")
    db_path: Path = Path("./data/ironview.db")


class ImportSettings(BaseSettings):
    # Configurable import keys; can be used later for Google Sheets IDs.
    platoon_loadout_label: str = "platoon_loadout"
    battalion_summary_label: str = "battalion_summary"
    form_responses_label: str = "form_responses"


class StatusTokens(BaseSettings):
    gap_tokens: list[str] = ["חוסר", "בלאי"]
    ok_tokens: list[str] = ["קיים", "יש"]

class GoogleSettings(BaseSettings):
    enabled: bool = True
    service_account_file: Optional[Path] = None
    api_key: Optional[str] = None
    oauth_client_id: Optional[str] = None
    oauth_client_secret: Optional[str] = None
    oauth_redirect_uri: Optional[str] = None
    file_ids: dict[str, dict[str, str] | list[str] | str] = {
        "platoon_loadout": "",
        "battalion_summary": "",
        "form_responses": {},
    }
    cache_dir: Path = Path("./data/sync_cache")
    max_retries: int = 3
    backoff_seconds: float = 1.0

class ThresholdSettings(BaseSettings):
    erosion_alert: float = 0.5

class SecuritySettings(BaseSettings):
    """
    Optional auth and request guardrails.
    """
    api_token: Optional[str] = None  # Bearer token or X-API-Key
    basic_user: Optional[str] = None
    basic_pass: Optional[str] = None
    require_auth_on_queries: bool = False
    max_upload_mb: int = 15  # Hard cap for uploads (Content-Length guard)
    authorized_users: dict[str, str] = {}

class LoggingSettings(BaseSettings):
    log_requests: bool = True
    format: str = "console"  # console | json
    level: str = "INFO"

class StorageSettings(BaseSettings):
    """
    Runtime persistence selection:
    - sqlite (local/dev default)
    - firestore (cloud stage A)
    """
    backend: str = "sqlite"  # sqlite|firestore
    firestore_project_id: Optional[str] = None
    firestore_database: str = "(default)"
    firestore_collection_prefix: str = "spearhead_v1"


class OperationalViewSettings(BaseSettings):
    """
    Fixed operational structure for command dashboard views.
    Keys map internal field families -> fixed sections.
    """
    sections: list[str] = ["Armament", "Logistics", "Communications"]
    section_display_names: dict[str, str] = {
        "Armament": "חימוש",
        "Logistics": "לוגיסטיקה",
        "Communications": "תקשוב",
    }
    company_order: list[str] = ["Kfir", "Mahatz", "Sufa"]
    enabled_companies: list[str] = ["Kfir", "Mahatz", "Sufa"]
    standards_path: Path = Path("./config/operational_standards.yaml")
    section_scope_notes: dict[str, str] = {
        "Armament": "אמצעים, חלפים, שמנים",
        "Logistics": "מקלעים, תחמושת, זיווד",
        "Communications": "ציוד, צופן תקלות",
    }
    family_to_section: dict[str, str] = {
        "ammo": "Logistics",
        "zivud": "Logistics",
        "kashpal": "Armament",
        "issues": "Communications",
        "parsim": "Armament",
        "means": "Communications",
        "communications_core": "Communications",
        "ranger": "Communications",
        "device_issue_matrix": "Communications",
        "office": "Communications",
    }
    critical_item_names: list[str] = [
        "חבל פריסה",
        "פטיש 5",
        "ראשוני",
        "איציק",
        "לום",
        'מאריך חש"ן',
        "בייבי קוני",
        "משלק",
        "פטיש קילו",
        "מפתח Y",
        "2מפתח פלטות",
        "בוקסה 1\\5\\16",
        "ידית כוח חצי",
        "ידית כוח 3\\4",
        "מחט ירי",
        "אלונקה",
        "מקלות חוטר",
    ]
    critical_gap_penalty: float = 12.0


class AISettings(BaseSettings):
    enabled: bool = False
    provider: str = "offline"  # offline|http
    base_url: Optional[str] = None  # used when provider=http
    api_key: Optional[str] = None
    model: str = "gpt-4o-mini"
    max_tokens: int = 1200
    cache_ttl_minutes: int = 60
    temperature: float = 0.2

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__", env_file=".env", extra="ignore")
    app: AppSettings = AppSettings()
    paths: PathSettings = PathSettings()
    imports: ImportSettings = ImportSettings()
    status_tokens: StatusTokens = StatusTokens()
    google: GoogleSettings = GoogleSettings()
    thresholds: ThresholdSettings = ThresholdSettings()
    security: SecuritySettings = SecuritySettings()
    logging: LoggingSettings = LoggingSettings()
    storage: StorageSettings = StorageSettings()
    operational: OperationalViewSettings = OperationalViewSettings()
    ai: AISettings = AISettings()

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "Settings":
        # Load from default path if exists
        default_path = Path("config/settings.yaml")
        path = config_path or (default_path if default_path.exists() else None)

        if not path:
            return cls()

        with open(path, "r") as f:
            config_data = yaml.safe_load(f)
        
        return cls(**config_data)

settings = Settings.load()
