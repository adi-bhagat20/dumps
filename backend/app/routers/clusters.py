import logging
from typing import List
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response, StreamingResponse

from app.database import get_db
from app.services.storage import storage_service
from app.services.zip_service import create_cluster_zip

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/clusters", tags=["clusters"])

@router.get("/{job_id}")
async def get_clusters(job_id: str):
    """
    Returns the cluster results for a completed job.
    """
    db = get_db()
    cluster_doc = await db.clusters.find_one({"job_id": job_id})
    if not cluster_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No clusters found for job {job_id}."
        )

    # Format clusters for API response
    clusters = cluster_doc.get("clusters", [])
    for c in clusters:
        if c.get("thumbnail_key"):
            c["thumbnail_url"] = storage_service.get_url(c["thumbnail_key"])
        else:
            c["thumbnail_url"] = None

    return {
        "job_id": job_id,
        "clusters": clusters
    }


@router.get("/{job_id}/{cluster_id}/photos")
async def get_cluster_photos(job_id: str, cluster_id: str):
    """
    Returns photo metadata and image URLs for a specific cluster.
    """
    db = get_db()
    cluster_doc = await db.clusters.find_one({"job_id": job_id})
    if not cluster_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No clusters found for job {job_id}."
        )

    target_cluster = None
    for c in cluster_doc.get("clusters", []):
        if c["cluster_id"] == cluster_id:
            target_cluster = c
            break

    if not target_cluster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cluster {cluster_id} not found."
        )

    photos = [
        {
            "photo_key": key,
            "url": storage_service.get_url(key),
            "filename": key.split("/")[-1]
        }
        for key in target_cluster.get("photo_keys", [])
    ]

    return {
        "cluster_id": cluster_id,
        "label": target_cluster["label"],
        "photo_count": len(photos),
        "photos": photos
    }


@router.get("/{job_id}/{cluster_id}/zip")
async def download_cluster_zip(job_id: str, cluster_id: str):
    """
    Generates and downloads a zip file containing only the photos of a person/cluster.
    """
    db = get_db()
    cluster_doc = await db.clusters.find_one({"job_id": job_id})
    if not cluster_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No clusters found for job {job_id}."
        )

    target_cluster = None
    for c in cluster_doc.get("clusters", []):
        if c["cluster_id"] == cluster_id:
            target_cluster = c
            break

    if not target_cluster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cluster {cluster_id} not found."
        )

    photo_keys = target_cluster.get("photo_keys", [])
    if not photo_keys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No photos found in cluster {cluster_id}."
        )

    cluster_label = target_cluster.get("label", "Person").replace(" ", "_")
    zip_bytes = create_cluster_zip(photo_keys, cluster_label)
    filename = f"dumps_{cluster_label.lower()}.zip"

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
