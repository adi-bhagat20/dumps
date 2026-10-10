import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    MONGO_URI: str = "mongodb://localhost:27017"
    DB_NAME: str = "dumps_db"
    STORAGE_PATH: str = "./storage"
    DEFAULT_USER_ID: str = "user_v1_placeholder"
    DBSCAN_EPS: float = 0.35
    DBSCAN_MIN_SAMPLES: int = 3
    RESCUE_THRESHOLD: float = 0.45
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Cloudflare R2 / S3 Configuration
    R2_ACCESS_KEY_ID: Optional[str] = None
    ACCESS_KEY_ID: Optional[str] = None
    R2_SECRET_ACCESS_KEY: Optional[str] = None
    SECRET_ACCESS_KEY: Optional[str] = None
    R2_ENDPOINT_URL: Optional[str] = None
    ENDPOINT_URL: Optional[str] = None
    R2_BUCKET_NAME: str = "dumps-photos"

    @property
    def r2_key(self) -> Optional[str]:
        val = self.R2_ACCESS_KEY_ID or self.ACCESS_KEY_ID
        return val.strip().strip("'\"") if val else None

    @property
    def r2_secret(self) -> Optional[str]:
        val = self.R2_SECRET_ACCESS_KEY or self.SECRET_ACCESS_KEY
        return val.strip().strip("'\"") if val else None

    @property
    def r2_endpoint(self) -> Optional[str]:
        val = self.R2_ENDPOINT_URL or self.ENDPOINT_URL
        return val.strip().strip("'\"") if val else None

    @property
    def is_r2_configured(self) -> bool:
        return bool(self.r2_key and self.r2_secret and self.r2_endpoint and self.R2_BUCKET_NAME)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
