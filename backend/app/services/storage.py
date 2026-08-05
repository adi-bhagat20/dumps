import os
import shutil
import logging
from pathlib import Path
from typing import List
from app.config import settings

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self, base_path: str = None):
        self.base_path = Path(base_path or settings.STORAGE_PATH).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)

    def get_upload_dir(self, upload_id: str) -> Path:
        upload_dir = self.base_path / str(upload_id)
        upload_dir.mkdir(parents=True, exist_ok=True)
        return upload_dir

    def get_thumbnails_dir(self, upload_id: str) -> Path:
        thumb_dir = self.base_path / str(upload_id) / "thumbnails"
        thumb_dir.mkdir(parents=True, exist_ok=True)
        return thumb_dir

    def save_bytes(self, upload_id: str, filename: str, content: bytes) -> str:
        upload_dir = self.get_upload_dir(upload_id)
        file_path = upload_dir / filename
        with open(file_path, "wb") as f:
            f.write(content)
        # Relative storage key
        return f"{upload_id}/{filename}"

    def get_full_path(self, storage_key: str) -> Path:
        return self.base_path / storage_key

    def file_exists(self, storage_key: str) -> bool:
        return self.get_full_path(storage_key).exists()

    def delete_upload_dir(self, upload_id: str):
        upload_dir = self.get_upload_dir(upload_id)
        if upload_dir.exists():
            shutil.rmtree(upload_dir)

storage_service = StorageService()
