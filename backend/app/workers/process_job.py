import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List

from app.database import get_db
from app.config import settings
from app.services.storage import storage_service
from app.services.face_pipeline import (
    detect_faces_in_image,
    dedupe_faces,
    cluster_and_rescue_faces,
    assign_photos_to_clusters,
    create_face_thumbnail,
    DetectedFace
)

logger = logging.getLogger(__name__)

# Dictionary holding SSE asyncio queues per job_id
job_queues: Dict[str, List[asyncio.Queue]] = {}

def register_job_queue(job_id: str) -> asyncio.Queue:
    queue = asyncio.Queue()
    if job_id not in job_queues:
        job_queues[job_id] = []
    job_queues[job_id].append(queue)
    return queue

def unregister_job_queue(job_id: str, queue: asyncio.Queue):
    if job_id in job_queues and queue in job_queues[job_id]:
        job_queues[job_id].remove(queue)
        if not job_queues[job_id]:
            del job_queues[job_id]

async def broadcast_event(job_id: str, event_data: dict):
    if job_id in job_queues:
        for q in list(job_queues[job_id]):
            await q.put(event_data)


async def run_pipeline_job(job_id: str, upload_id: str):
    db = get_db()
    logger.info(f"Starting background job {job_id} for upload {upload_id}...")

    try:
        # Update job status to processing
        await db.jobs.update_one(
            {"_id": job_id},
            {"$set": {"status": "processing"}}
        )

        upload_doc = await db.uploads.find_one({"_id": upload_id})
        if not upload_doc:
            raise ValueError(f"Upload document {upload_id} not found")

        files = upload_doc.get("files", [])
        total_photos = len(files)

        await db.jobs.update_one(
            {"_id": job_id},
            {"$set": {"total_photos": total_photos}}
        )

        all_detected_faces: List[DetectedFace] = []
        faces_by_photo: Dict[str, List[DetectedFace]] = {}
        photo_keys: List[str] = []

        processed_count = 0

        for file_info in files:
            storage_key = file_info["storage_key"]
            photo_keys.append(storage_key)
            full_path = storage_service.get_full_path(storage_key)

            if full_path.exists():
                # Detect faces in CPU
                # Run in executor to avoid blocking event loop during CV/PyTorch/ONNX computation
                loop = asyncio.get_running_loop()
                raw_faces = await loop.run_in_executor(None, detect_faces_in_image, storage_key, full_path)
                deduped_faces = dedupe_faces(raw_faces)
                
                faces_by_photo[storage_key] = deduped_faces
                all_detected_faces.extend(deduped_faces)

            processed_count += 1

            # Periodically release memory back to OS
            import gc
            gc.collect()

            # Update job progress in MongoDB
            await db.jobs.update_one(
                {"_id": job_id},
                {"$set": {"processed_photos": processed_count}}
            )

            # Broadcast SSE progress event
            await broadcast_event(job_id, {
                "type": "progress",
                "processed": processed_count,
                "total": total_photos
            })

        logger.info(f"Detected {len(all_detected_faces)} total faces across {total_photos} photos for job {job_id}.")

        # Run DBSCAN + rescue pass in executor
        loop = asyncio.get_running_loop()
        clustered_faces_map = await loop.run_in_executor(
            None,
            cluster_and_rescue_faces,
            all_detected_faces
        )

        # Prominent-face assignment pass
        cluster_to_photos, repr_faces = assign_photos_to_clusters(photo_keys, faces_by_photo)

        # Prepare cluster summaries and thumbnails
        cluster_summaries = []
        face_records = []

        # Sort cluster IDs (person_0, person_1, ..., unsorted at end)
        sorted_cids = sorted(
            [c for c in cluster_to_photos.keys() if c != "unsorted"],
            key=lambda x: int(x.split("_")[1]) if "_" in x and x.split("_")[1].isdigit() else 999
        )
        if "unsorted" in cluster_to_photos:
            sorted_cids.append("unsorted")

        for cid in sorted_cids:
            assigned_keys = cluster_to_photos[cid]
            if not assigned_keys:
                continue

            if cid == "unsorted":
                label = "Unsorted"
                thumb_key = None
            else:
                person_num = cid.split("_")[1] if "_" in cid else cid
                label = f"Person {int(person_num) + 1}"
                
                # Generate thumbnail if representative face exists
                repr_face = repr_faces.get(cid)
                if repr_face:
                    thumb_key = await loop.run_in_executor(
                        None,
                        create_face_thumbnail,
                        upload_id,
                        cid,
                        repr_face
                    )
                else:
                    thumb_key = None

            cluster_summaries.append({
                "cluster_id": cid,
                "label": label,
                "thumbnail_key": thumb_key,
                "photo_count": len(assigned_keys),
                "photo_keys": assigned_keys
            })

        # Save all face records for DB
        for face in all_detected_faces:
            face_records.append({
                "photo_key": face.photo_key,
                "bbox": face.bbox,
                "confidence": face.confidence,
                "cluster_id": face.cluster_id
            })

        # Create Cluster document in MongoDB
        cluster_doc = {
            "user_id": settings.DEFAULT_USER_ID,
            "job_id": job_id,
            "upload_id": upload_id,
            "clusters": cluster_summaries,
            "faces": face_records,
            "created_at": datetime.now(timezone.utc)
        }
        await db.clusters.insert_one(cluster_doc)

        # Mark job completed
        await db.jobs.update_one(
            {"_id": job_id},
            {
                "$set": {
                    "status": "completed",
                    "completed_at": datetime.now(timezone.utc)
                }
            }
        )

        logger.info(f"Job {job_id} completed successfully with {len(cluster_summaries)} clusters.")

        # Broadcast SSE completion event
        await broadcast_event(job_id, {
            "type": "completed",
            "clusters": cluster_summaries
        })

    except Exception as e:
        logger.exception(f"Job {job_id} failed with exception: {e}")
        await db.jobs.update_one(
            {"_id": job_id},
            {
                "$set": {
                    "status": "failed",
                    "error": str(e)
                }
            }
        )
        await broadcast_event(job_id, {
            "type": "error",
            "error": str(e)
        })
