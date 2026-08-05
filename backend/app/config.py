import os
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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
