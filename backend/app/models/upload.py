from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field

class FileMetadata(BaseModel):
    filename: str
    original_name: str
    storage_key: str
    content_type: str
    size_bytes: int

class UploadDocument(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    user_id: str
    folder_name: str
    file_count: int
    files: List[FileMetadata]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {
        "populate_by_name": True
    }
