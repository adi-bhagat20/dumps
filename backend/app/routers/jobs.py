import json
import asyncio
import uuid
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from bson import ObjectId

from app.database import get_db
from app.config import settings
from app.workers.process_job import (
    run_pipeline_job,
    register_job_queue,
    unregister_job_queue
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/jobs", tags=["jobs"])

@router.post("/{upload_id}/start")
async def start_job(upload_id: str):
    """
    Starts an async face clustering job for an uploaded folder.
    Returns the job_id immediately.
    """
    db = get_db()
    upload_doc = await db.uploads.find_one({"_id": upload_id})
    if not upload_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload {upload_id} not found."
        )

    job_id = str(uuid.uuid4())
    job_doc = {
        "_id": job_id,
        "user_id": settings.DEFAULT_USER_ID,
        "upload_id": upload_id,
        "status": "pending",
        "total_photos": upload_doc.get("file_count", 0),
        "processed_photos": 0,
        "error": None,
        "created_at": datetime.now(timezone.utc),
        "completed_at": None
    }
    await db.jobs.insert_one(job_doc)

    # Launch processing pipeline as background task
    asyncio.create_task(run_pipeline_job(job_id, upload_id))

    return {
        "job_id": job_id,
        "upload_id": upload_id,
        "status": "pending"
    }


@router.get("/{job_id}/stream")
async def stream_job_progress(job_id: str):
    """
    SSE stream endpoint pushing live progress counter and completion events to the frontend.
    """
    db = get_db()
    job_doc = await db.jobs.find_one({"_id": job_id})
    if not job_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found."
        )

    queue = register_job_queue(job_id)

    async def event_generator():
        try:
            # Send initial state snapshot if job already in progress/completed
            current_job = await db.jobs.find_one({"_id": job_id})
            if current_job:
                status = current_job.get("status")
                if status == "completed":
                    cluster_doc = await db.clusters.find_one({"job_id": job_id})
                    clusters = cluster_doc.get("clusters", []) if cluster_doc else []
                    data = json.dumps({"type": "completed", "clusters": clusters})
                    yield f"data: {data}\n\n"
                    return
                elif status == "failed":
                    data = json.dumps({"type": "error", "error": current_job.get("error")})
                    yield f"data: {data}\n\n"
                    return
                else:
                    data = json.dumps({
                        "type": "progress",
                        "processed": current_job.get("processed_photos", 0),
                        "total": current_job.get("total_photos", 0)
                    })
                    yield f"data: {data}\n\n"

            # Stream real-time events from queue
            while True:
                event = await queue.get()
                event_str = json.dumps(event)
                yield f"data: {event_str}\n\n"
                if event.get("type") in ("completed", "error"):
                    break
        except asyncio.CancelledError:
            logger.info(f"SSE client disconnected for job {job_id}")
        finally:
            unregister_job_queue(job_id, queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
