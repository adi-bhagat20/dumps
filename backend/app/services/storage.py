import os
import shutil
import logging
from pathlib import Path
from typing import List, Optional
from app.config import settings

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self, base_path: str = None):
        self.base_path = Path(base_path or settings.STORAGE_PATH).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.s3_client = None
        self.bucket_name = settings.R2_BUCKET_NAME

        if settings.is_r2_configured:
            try:
                import boto3
                from botocore.config import Config

                self.s3_client = boto3.client(
                    service_name="s3",
                    endpoint_url=settings.r2_endpoint,
                    aws_access_key_id=settings.r2_key,
                    aws_secret_access_key=settings.r2_secret,
                    region_name="auto",
                    config=Config(
                        signature_version="s3v4",
                        retries={"max_attempts": 3, "mode": "standard"}
                    )
                )
                logger.info(f"Cloudflare R2 storage initialized (bucket: '{self.bucket_name}').")
            except Exception as e:
                logger.warning(f"Could not initialize Cloudflare R2 client ({e}). Falling back to local disk.")
                self.s3_client = None
        else:
            logger.info("Cloudflare R2 not configured. Using local disk storage.")

    @property
    def is_cloud(self) -> bool:
        return self.s3_client is not None

    def get_upload_dir(self, upload_id: str) -> Path:
        upload_dir = self.base_path / str(upload_id)
        upload_dir.mkdir(parents=True, exist_ok=True)
        return upload_dir

    def get_thumbnails_dir(self, upload_id: str) -> Path:
        thumb_dir = self.base_path / str(upload_id) / "thumbnails"
        thumb_dir.mkdir(parents=True, exist_ok=True)
        return thumb_dir

    def save_upload_file(self, upload_id: str, filename: str, upload_file, content_type: str = "image/jpeg") -> tuple:
        """
        Stream an UploadFile directly to local disk in 64KB chunks and to Cloudflare R2
        without buffering the entire file in RAM.
        """
        storage_key = f"{upload_id}/{filename}"
        upload_dir = self.get_upload_dir(upload_id)
        file_path = upload_dir / filename

        # 1. Stream in 64KB chunks to local disk
        with open(file_path, "wb") as f:
            shutil.copyfileobj(upload_file.file, f, length=65536)

        size_bytes = file_path.stat().st_size

        # 2. Upload to Cloudflare R2 via upload_file (streams from disk directly)
        if self.is_cloud:
            try:
                self.s3_client.upload_file(
                    Filename=str(file_path),
                    Bucket=self.bucket_name,
                    Key=storage_key,
                    ExtraArgs={"ContentType": content_type}
                )
                logger.debug(f"Streamed {storage_key} to Cloudflare R2.")
            except Exception as e:
                logger.error(f"Failed to stream {storage_key} to R2: {e}")

        return storage_key, size_bytes

    def save_bytes(self, upload_id: str, filename: str, content: bytes, content_type: str = "image/jpeg") -> str:
        storage_key = f"{upload_id}/{filename}"
        
        # 1. Save to local cache directory for instant ML pipeline processing
        upload_dir = self.get_upload_dir(upload_id)
        file_path = upload_dir / filename
        with open(file_path, "wb") as f:
            f.write(content)

        # 2. Upload to Cloudflare R2 if configured (stream from disk)
        if self.is_cloud:
            try:
                self.s3_client.upload_file(
                    Filename=str(file_path),
                    Bucket=self.bucket_name,
                    Key=storage_key,
                    ExtraArgs={"ContentType": content_type}
                )
                logger.debug(f"Uploaded {storage_key} to Cloudflare R2.")
            except Exception as e:
                logger.error(f"Failed to upload {storage_key} to R2: {e}")

        return storage_key

    def save_thumbnail_bytes(self, upload_id: str, filename: str, content: bytes) -> str:
        storage_key = f"{upload_id}/thumbnails/{filename}"

        # 1. Save to local cache
        thumb_dir = self.get_thumbnails_dir(upload_id)
        file_path = thumb_dir / filename
        with open(file_path, "wb") as f:
            f.write(content)

        # 2. Upload to Cloudflare R2
        if self.is_cloud:
            try:
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=storage_key,
                    Body=content,
                    ContentType="image/jpeg"
                )
                logger.debug(f"Uploaded thumbnail {storage_key} to Cloudflare R2.")
            except Exception as e:
                logger.error(f"Failed to upload thumbnail {storage_key} to R2: {e}")

        return storage_key

    def get_full_path(self, storage_key: str) -> Path:
        """
        Returns local filesystem Path to file.
        If file is missing locally but exists in R2, downloads it on-demand to cache.
        """
        local_path = self.base_path / storage_key
        if not local_path.exists() and self.is_cloud:
            try:
                local_path.parent.mkdir(parents=True, exist_ok=True)
                resp = self.s3_client.get_object(Bucket=self.bucket_name, Key=storage_key)
                with open(local_path, "wb") as f:
                    f.write(resp["Body"].read())
                logger.debug(f"Downloaded {storage_key} from R2 to local cache.")
            except Exception as e:
                logger.error(f"Failed to fetch {storage_key} from R2: {e}")
        return local_path

    def get_bytes(self, storage_key: str) -> Optional[bytes]:
        """
        Retrieves file bytes from local cache or directly from Cloudflare R2.
        """
        local_path = self.base_path / storage_key
        if local_path.exists():
            with open(local_path, "rb") as f:
                return f.read()

        if self.is_cloud:
            try:
                resp = self.s3_client.get_object(Bucket=self.bucket_name, Key=storage_key)
                return resp["Body"].read()
            except Exception as e:
                logger.error(f"Failed to retrieve bytes for {storage_key} from R2: {e}")
                return None

        return None

    def get_url(self, storage_key: str, expires_in: int = 86400) -> str:
        """
        Generates a direct pre-signed Cloudflare R2 URL (default valid for 24h),
        or falls back to local relative static URL /storage/{key}.
        """
        if self.is_cloud:
            try:
                return self.s3_client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.bucket_name, "Key": storage_key},
                    ExpiresIn=expires_in
                )
            except Exception as e:
                logger.error(f"Failed to generate pre-signed URL for {storage_key}: {e}")

        # Fallback to local server static path
        return f"/storage/{storage_key}"

    def file_exists(self, storage_key: str) -> bool:
        local_path = self.base_path / storage_key
        if local_path.exists():
            return True
        if self.is_cloud:
            try:
                self.s3_client.head_object(Bucket=self.bucket_name, Key=storage_key)
                return True
            except Exception:
                return False
        return False

    def delete_upload_dir(self, upload_id: str):
        # 1. Delete all R2 objects with prefix
        if self.is_cloud:
            try:
                prefix = f"{upload_id}/"
                paginator = self.s3_client.get_paginator("list_objects_v2")
                for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                    objects_to_delete = [{"Key": obj["Key"]} for obj in page.get("Contents", [])]
                    if objects_to_delete:
                        self.s3_client.delete_objects(
                            Bucket=self.bucket_name,
                            Delete={"Objects": objects_to_delete}
                        )
                logger.info(f"Deleted upload folder {upload_id} from R2.")
            except Exception as e:
                logger.error(f"Failed to delete upload {upload_id} from R2: {e}")

        # 2. Delete local directory
        upload_dir = self.base_path / str(upload_id)
        if upload_dir.exists():
            shutil.rmtree(upload_dir)

storage_service = StorageService()
