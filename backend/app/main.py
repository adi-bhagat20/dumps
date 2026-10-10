import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import settings
from app.database import connect_to_mongo, close_mongo_connection
from app.services.face_pipeline import init_face_model
from app.routers import uploads, jobs, clusters

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("dumps_backend")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing DUMPS backend service...")
    await connect_to_mongo()
    # Pre-initialize InsightFace model at startup
    init_face_model()
    yield
    await close_mongo_connection()
    logger.info("DUMPS backend shutdown complete.")

app = FastAPI(
    title="DUMPS API",
    description="Auto-sort photo dumps into per-person downloadable zips",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow local dev frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(uploads.router)
app.include_router(jobs.router)
app.include_router(clusters.router)

# Mount local storage folder for serving thumbnail and raw image files
storage_path = Path(settings.STORAGE_PATH).resolve()
storage_path.mkdir(parents=True, exist_ok=True)
app.mount("/storage", StaticFiles(directory=str(storage_path)), name="storage")

@app.get("/api/health")
async def health_check():
    db_status = "connected"
    try:
        from app.database import db_manager
        if db_manager.client is not None:
            await db_manager.client.admin.command('ping')
        else:
            db_status = "disconnected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "service": "dumps-api",
        "database": db_status,
        "version": "1.0.0"
    }
