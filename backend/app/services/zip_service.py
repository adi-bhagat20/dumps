import io
import zipfile
import logging
from pathlib import Path
from typing import List
from app.services.storage import storage_service

logger = logging.getLogger(__name__)

def create_cluster_zip(photo_keys: List[str], cluster_name: str) -> bytes:
    """
    Creates an in-memory zip archive containing all photos for a cluster.
    """
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for key in photo_keys:
            data = storage_service.get_bytes(key)
            if data:
                filename = Path(key).name
                zf.writestr(filename, data)
            else:
                logger.warning(f"File missing when creating zip: {key}")

    zip_buffer.seek(0)
    return zip_buffer.getvalue()
