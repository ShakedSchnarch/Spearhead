from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
import yaml

class AppSettings(BaseSettings):
    name: str = "Spearhead"
    version: str = "1.0.0"
    theme: str = "tactical_flat.css"  # Default theme

class PathSettings(BaseSettings):
    input_dir: Path = Path("./data/input")
    output_dir: Path = Path("./reports")
    templates_dir: Path = Path("./templates")
    assets_dir: Path = Path("./assets")
    db_path: Path = Path("./data/spearhead.db")


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
    file_ids: dict[str, str | list[str]] = {
        "platoon_loadout": "1kkdR41tCHJQQDCGMLzch-YCcxMiM1uSp-5MrEl9AAVY", # Machatz placeholder if same sheet, or use separate logic
        "battalion_summary": "",
        "form_responses": [
            "1kkdR41tCHJQQDCGMLzch-YCcxMiM1uSp-5MrEl9AAVY", # Machatz
            "11yfVvw2IcXQZUkfO1K69DwMXNUwBd-ffW7eWOpP2g6M", # Sufa
             "1Jc8mEjAVMfuMoLTpVXG_C0anO1njy88q3MJfU6sTl3Y", # Kfir
        ],
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

class LoggingSettings(BaseSettings):
    log_requests: bool = True

class AISettings(BaseSettings):
    enabled: bool = False
    provider: str = "offline"  # offline|http
    base_url: Optional[str] = None  # used when provider=http
    api_key: Optional[str] = None
    model: str = "gpt-4o-mini"
    max_tokens: int = 256
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
