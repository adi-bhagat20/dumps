import os
import cv2
import numpy as np
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from PIL import Image
import insightface
from insightface.app import FaceAnalysis
from sklearn.cluster import DBSCAN

from app.config import settings
from app.services.storage import storage_service

logger = logging.getLogger(__name__)

# Global model instance initialized once at startup
_face_app: Optional[FaceAnalysis] = None

def init_face_model():
    global _face_app
    if _face_app is None:
        logger.info("Initializing InsightFace model (low-memory mode)...")
        import onnxruntime as ort

        # Enforce single-thread execution and disable large memory arenas to prevent multi-core RAM explosion
        sess_options = ort.SessionOptions()
        sess_options.intra_op_num_threads = 1
        sess_options.inter_op_num_threads = 1
        sess_options.enable_cpu_mem_arena = False
        sess_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL

        app = FaceAnalysis(
            name="buffalo_s",
            providers=['CPUExecutionProvider'],
            allowed_modules=['detection', 'recognition'],
            sess_options=sess_options
        )
        app.prepare(ctx_id=-1, det_size=(640, 640))
        _face_app = app
        logger.info("InsightFace model initialized successfully.")
    return _face_app

def get_face_model() -> FaceAnalysis:
    if _face_app is None:
        return init_face_model()
    return _face_app


class DetectedFace:
    def __init__(self, photo_key: str, bbox: List[int], confidence: float, embedding: np.ndarray, area: float):
        self.photo_key = photo_key
        self.bbox = bbox  # [x1, y1, x2, y2]
        self.confidence = float(confidence)
        self.embedding = embedding  # 512-D vector
        self.area = float(area)
        self.cluster_id: str = "unsorted"


def compute_iou(boxA: List[int], boxB: List[int]) -> float:
    """Compute Intersection over Union (IoU) of two bounding boxes [x1, y1, x2, y2]."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interArea = max(0, xB - xA) * max(0, yB - yA)
    if interArea == 0:
        return 0.0

    boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

    iou = interArea / float(boxAArea + boxBArea - interArea)
    return iou


def detect_faces_in_image(photo_key: str, image_path: Path) -> List[DetectedFace]:
    """Stage 1: Detect faces in an image using InsightFace."""
    model = get_face_model()
    img = cv2.imread(str(image_path))
    if img is None:
        logger.warning(f"Could not load image: {image_path}")
        return []

    # Resize long edge to 640px if larger, keeping aspect ratio for inference speed
    h, w = img.shape[:2]
    max_dim = max(h, w)
    if max_dim > 640:
        scale = 640.0 / max_dim
        new_w, new_h = int(w * scale), int(h * scale)
        img_resized = cv2.resize(img, (new_w, new_h))
        del img  # Immediately free raw high-res bitmap (up to 60MB) before ONNX inference
    else:
        img_resized = img

    raw_faces = model.get(img_resized)
    del img_resized
    faces: List[DetectedFace] = []

    for raw_face in raw_faces:
        if raw_face.embedding is None:
            continue
        
        # Scale bounding box back to original image dimensions
        bbox = raw_face.bbox / scale
        x1, y1, x2, y2 = [int(v) for v in bbox]
        # Ensure bounding box is within image bounds
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        
        area = (x2 - x1) * (y2 - y1)
        embedding = raw_face.embedding / np.linalg.norm(raw_face.embedding)  # L2 normalize
        
        faces.append(DetectedFace(
            photo_key=photo_key,
            bbox=[x1, y1, x2, y2],
            confidence=float(raw_face.det_score),
            embedding=embedding,
            area=area
        ))

    return faces


def dedupe_faces(faces: List[DetectedFace], iou_threshold: float = 0.5) -> List[DetectedFace]:
    """Stage 2: Dedupe overlapping face detections within the same photo."""
    if len(faces) <= 1:
        return faces

    # Sort faces by confidence descending
    sorted_faces = sorted(faces, key=lambda f: f.confidence, reverse=True)
    kept_faces: List[DetectedFace] = []

    for face in sorted_faces:
        duplicate = False
        for kept in kept_faces:
            if compute_iou(face.bbox, kept.bbox) > iou_threshold:
                duplicate = True
                break
        if not duplicate:
            kept_faces.append(face)

    return kept_faces


def cluster_and_rescue_faces(
    all_faces: List[DetectedFace],
    eps: float = None,
    min_samples: int = None,
    rescue_threshold: float = None
) -> Dict[str, List[DetectedFace]]:
    """Stage 3: Cluster embeddings with DBSCAN and run centroid rescue pass."""
    eps = eps or settings.DBSCAN_EPS
    min_samples = min_samples or settings.DBSCAN_MIN_SAMPLES
    rescue_threshold = rescue_threshold or settings.RESCUE_THRESHOLD

    if not all_faces:
        return {"unsorted": []}

    # Extract normalized 512-D embeddings
    embeddings = np.array([f.embedding for f in all_faces])

    # DBSCAN with cosine distance
    dbscan = DBSCAN(eps=eps, min_samples=min_samples, metric="cosine")
    labels = dbscan.fit_predict(embeddings)

    clusters: Dict[str, List[DetectedFace]] = {}
    unsorted: List[DetectedFace] = []

    for label, face in zip(labels, all_faces):
        if label == -1:
            face.cluster_id = "unsorted"
            unsorted.append(face)
        else:
            cluster_id = f"person_{label}"
            face.cluster_id = cluster_id
            if cluster_id not in clusters:
                clusters[cluster_id] = []
            clusters[cluster_id].append(face)

    # Centroid rescue pass for unsorted faces
    if clusters and unsorted:
        centroids: Dict[str, np.ndarray] = {}
        for cid, faces in clusters.items():
            mean_emb = np.mean([f.embedding for f in faces], axis=0)
            centroids[cid] = mean_emb / np.linalg.norm(mean_emb)

        rescued: List[DetectedFace] = []
        for face in unsorted:
            best_cid = None
            best_sim = -1.0
            for cid, centroid in centroids.items():
                sim = float(np.dot(face.embedding, centroid))  # Cosine similarity for unit vectors
                dist = 1.0 - sim  # Cosine distance
                if dist < rescue_threshold and sim > best_sim:
                    best_sim = sim
                    best_cid = cid

            if best_cid is not None:
                face.cluster_id = best_cid
                clusters[best_cid].append(face)
                rescued.append(face)

        # Remove rescued faces from unsorted list
        unsorted = [f for f in unsorted if f not in rescued]

    clusters["unsorted"] = unsorted
    return clusters


def assign_photos_to_clusters(
    photo_keys: List[str],
    faces_by_photo: Dict[str, List[DetectedFace]]
) -> Tuple[Dict[str, List[str]], Dict[str, DetectedFace]]:
    """
    Stage 4: Prominent-face rule — assign each image to exactly one folder.
    For photos with 2+ detected faces, pick the person with the largest bounding box area.
    Returns:
      - map of cluster_id -> list of assigned photo_keys
      - map of cluster_id -> representative face (largest area face in cluster for thumbnail)
    """
    cluster_to_photos: Dict[str, List[str]] = {}
    representative_faces: Dict[str, DetectedFace] = {}

    for photo_key in photo_keys:
        faces = faces_by_photo.get(photo_key, [])
        if not faces:
            # No face detected -> unsorted
            cluster_id = "unsorted"
        else:
            # Prominent face rule: select face with maximum bounding box area
            prominent_face = max(faces, key=lambda f: f.area)
            cluster_id = prominent_face.cluster_id

        if cluster_id not in cluster_to_photos:
            cluster_to_photos[cluster_id] = []
        cluster_to_photos[cluster_id].append(photo_key)

        # Track representative face per cluster (largest bbox area across photos)
        if faces and cluster_id != "unsorted":
            best_face = max(faces, key=lambda f: f.area)
            if cluster_id not in representative_faces or best_face.area > representative_faces[cluster_id].area:
                representative_faces[cluster_id] = best_face

    return cluster_to_photos, representative_faces


def create_face_thumbnail(upload_id: str, cluster_id: str, face: DetectedFace) -> Optional[str]:
    """Crops the representative face from original image and saves thumbnail."""
    try:
        source_path = storage_service.get_full_path(face.photo_key)
        if not source_path.exists():
            return None

        with Image.open(source_path) as img:
            img = img.convert("RGB")
            w, h = img.size
            x1, y1, x2, y2 = face.bbox
            
            # Expand bbox slightly for contextual margin
            bw, bh = x2 - x1, y2 - y1
            margin_x = int(bw * 0.3)
            margin_y = int(bh * 0.3)
            
            crop_x1 = max(0, x1 - margin_x)
            crop_y1 = max(0, y1 - margin_y)
            crop_x2 = min(w, x2 + margin_x)
            crop_y2 = min(h, y2 + margin_y)
            
            cropped = img.crop((crop_x1, crop_y1, crop_x2, crop_y2))
            cropped.thumbnail((250, 250))
            
            import io
            thumb_buffer = io.BytesIO()
            cropped.save(thumb_buffer, "JPEG", quality=90)
            thumb_filename = f"{cluster_id}_thumb.jpg"
            return storage_service.save_thumbnail_bytes(upload_id, thumb_filename, thumb_buffer.getvalue())
    except Exception as e:
        logger.error(f"Failed to create face thumbnail for {cluster_id}: {e}")
        return None
