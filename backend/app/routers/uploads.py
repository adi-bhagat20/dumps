import io
import os
import uuid
import logging
from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from PIL import Image
import pillow_heif

from app.database import get_db
from app.config import settings
from app.services.storage import storage_service

# Register HEIC opener with Pillow
pillow_heif.register_heif_opener()

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/uploads", tags=["uploads"])

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic"}

@router.post("")
async def upload_folder(
    folder_name: str = Form("Photos"),
    files: List[UploadFile] = File(...)
):
    """
    Uploads a batch/folder of photos.
    Converts HEIC images to JPEG on upload.
    Saves image files to local storage and metadata to MongoDB.
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided in upload request."
        )

    db = get_db()
    upload_id = str(uuid.uuid4())
    saved_files = []

    for file in files:
        filename = file.filename or "photo.jpg"
        ext = os.path.splitext(filename)[1].lower()

        if ext not in ALLOWED_EXTENSIONS:
            logger.info(f"Skipping unsupported non-image file: {filename}")
            continue

        if ext == ".heic":
            # Handle HEIC conversion
            try:
                content = await file.read()
                if not content:
                    continue
                img = Image.open(io.BytesIO(content))
                img = img.convert("RGB")
                out_buffer = io.BytesIO()
                img.save(out_buffer, format="JPEG", quality=90)
                jpeg_bytes = out_buffer.getvalue()
                
                base_name = os.path.splitext(os.path.basename(filename))[0]
                storage_filename = f"{base_name}_{uuid.uuid4().hex[:6]}.jpg"
                content_type = "image/jpeg"
                storage_key = storage_service.save_bytes(upload_id, storage_filename, jpeg_bytes, content_type)
                size_bytes = len(jpeg_bytes)

                del img, out_buffer, content, jpeg_bytes
            except Exception as e:
                logger.error(f"Failed HEIC conversion for {filename}: {e}")
                continue
        else:
            base_name = os.path.splitext(os.path.basename(filename))[0]
            storage_filename = f"{base_name}_{uuid.uuid4().hex[:6]}{ext}"
            content_type = file.content_type or "image/jpeg"
            
            # Stream directly in chunks to disk & R2 without loading bytes into Python memory
            storage_key, size_bytes = storage_service.save_upload_file(
                upload_id, storage_filename, file, content_type
            )

        saved_files.append({
            "filename": storage_filename,
            "original_name": os.path.basename(filename),
            "storage_key": storage_key,
            "content_type": content_type,
            "size_bytes": size_bytes
        })

        import gc
        gc.collect()

    if not saved_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid image files (JPG, PNG, HEIC) found in the upload."
        )

    # Insert upload document into MongoDB
    upload_doc = {
        "_id": upload_id,  # store string ID for clean retrieval
        "user_id": settings.DEFAULT_USER_ID,
        "folder_name": folder_name,
        "file_count": len(saved_files),
        "files": saved_files,
        "created_at": datetime.now(timezone.utc)
    }

    await db.uploads.insert_one(upload_doc)
    logger.info(f"Created upload {upload_id} with {len(saved_files)} image files.")

    return {
        "upload_id": upload_id,
        "folder_name": folder_name,
        "file_count": len(saved_files)
    }
