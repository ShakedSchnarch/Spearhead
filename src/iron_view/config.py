from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
import yaml

class AppSettings(BaseSettings):
    name: str = "Iron-View"
    version: str = "1.0.0"
    theme: str = "tactical_flat.css"  # Default theme

class PathSettings(BaseSettings):
    input_dir: Path = Path("./data/input")
    output_dir: Path = Path("./reports")
    templates_dir: Path = Path("./templates")
    assets_dir: Path = Path("./assets")

class ThresholdSettings(BaseSettings):
    erosion_alert: float = 0.5

class Settings(BaseSettings):
    app: AppSettings = AppSettings()
    paths: PathSettings = PathSettings()
    thresholds: ThresholdSettings = ThresholdSettings()

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
