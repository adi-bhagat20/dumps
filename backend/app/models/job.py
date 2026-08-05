from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field

class JobDocument(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    user_id: str
    upload_id: str
    status: str = "pending"  # "pending", "processing", "completed", "failed"
    total_photos: int = 0
    processed_photos: int = 0
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

    model_config = {
        "populate_by_name": True
    }
