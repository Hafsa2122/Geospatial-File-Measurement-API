from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    PROJECT_NAME: str = "Geospatial File Measurement API"
    PROJECT_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    MAX_UPLOAD_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB limit
    DEFAULT_CRS: str = "EPSG:4326"
    ALLOWED_EXTENSIONS: set[str] = {".zip", ".kml"}
    
    # Storage Directory
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

settings = Settings()
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
