from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field

class ClusterSummary(BaseModel):
    cluster_id: str             # "person_0", "person_1", ... or "unsorted"
    label: str                  # "Person 1", "Unsorted", etc.
    thumbnail_key: Optional[str] = None  # storage key for representative face crop
    photo_count: int
    photo_keys: List[str]       # storage keys of assigned photos

class FaceRecord(BaseModel):
    photo_key: str
    bbox: List[int]             # [x1, y1, x2, y2]
    confidence: float
    cluster_id: str

class ClusterDocument(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    user_id: str
    job_id: str
    upload_id: str
    clusters: List[ClusterSummary]
    faces: List[FaceRecord]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {
        "populate_by_name": True
    }
