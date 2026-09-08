# 📸 DUMPS — Auto-Sort Photo Dumps by Person

> **Drop in a chaotic folder of event photos. Get back per-person collections, each downloadable as a zip — zero manual tagging required.**

DUMPS is a full-stack AI-powered web application built for events, weddings, and group shoots. It uses face detection and unsupervised clustering to automatically separate a mixed folder of photos into one sub-collection per person — with live progress updates and instant zip downloads.

> ⚠️ **Current Status:** This project runs fully on a **local machine** (local MongoDB + local disk storage). Cloud deployment and MongoDB Atlas migration are planned future milestones — see [Future Scope](#-future-scope) below.

---

## ✨ Features

| Feature | Details |
|---|---|
| 📁 **Folder Upload** | Browser folder picker for `JPG`, `PNG`, and `HEIC` images |
| 🍎 **HEIC Support** | Apple `.heic` files are auto-converted to JPEG server-side before analysis |
| 🤖 **AI Face Clustering** | 4-stage ML pipeline: Detect → Dedupe → Cluster → Assign |
| 📡 **Real-Time Progress** | Live counter pushed via Server-Sent Events (SSE) — no polling |
| 🖼️ **Per-Person Gallery** | View a photo gallery for any detected person |
| 📦 **Zip Downloads** | Streaming zip generation per person or the "Unsorted" bucket |
| 🔒 **Privacy-First** | All photos auto-expire and are deleted after 24 hours |

---

## 🧠 The Face Processing Pipeline

This is the core of DUMPS. Every upload goes through a 4-stage pipeline:

```
Stage 1 — Detect
  InsightFace (buffalo_s, CPU mode) detects all faces in each photo
  and extracts a 512-dimensional embedding per face.
  Images are resized to max 640px on the long edge for inference speed.

Stage 2 — Deduplicate
  Within each image, overlapping bounding boxes are deduplicated
  using an IoU (Intersection over Union) filter > 0.5.
  Lower-confidence duplicate detections are dropped.

Stage 3 — Cluster & Rescue
  All embeddings across all photos are clustered using DBSCAN
  (eps=0.35, min_samples=3, cosine distance metric).
  A centroid rescue pass then re-assigns outlier faces (label=-1)
  that fall within rescue_threshold=0.45 cosine distance of any cluster centroid.

Stage 4 — Prominent-Face Assignment
  Every photo is assigned to exactly one person folder.
  For group shots with multiple detected faces, the person
  with the largest bounding box area "wins" and owns that photo.
  Photos with no detected face go to the "Unsorted" collection.
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Browser (React + Vite)             │
│  UploadZone → ProgressBar (SSE) → PersonGrid → Gallery  │
└──────────────────────┬──────────────────────────────────┘
                       │  REST + SSE
┌──────────────────────▼──────────────────────────────────┐
│                  FastAPI Backend (Python 3.12)           │
│                                                         │
│  POST /api/uploads          — Ingest & store photos     │
│  POST /api/jobs/{id}/start  — Kick off clustering job   │
│  GET  /api/jobs/{id}/stream — SSE progress stream       │
│  GET  /api/clusters/{id}    — Fetch cluster results     │
│  GET  /api/clusters/{job}/{cluster}/photos — Gallery    │
│  GET  /api/clusters/{job}/{cluster}/zip — Download zip  │
│                                                         │
│  Background Worker (asyncio.create_task)                │
│    └── Face pipeline runs in thread pool executor       │
│        (avoids blocking the async event loop)           │
└──────┬─────────────────┬───────────────────────────────┘
       │                 │
┌──────▼──────┐   ┌──────▼──────┐
│  MongoDB    │   │ Local Disk  │
│  (Motor)    │   │  Storage    │
│             │   │             │
│ Currently:  │   │ Currently:  │
│ localhost   │   │ ./storage/  │
│             │   │             │
│ Planned:    │   │ Planned:    │
│ Atlas (SRV) │   │  AWS S3/R2  │
└─────────────┘   └─────────────┘
```

---

## 🛠️ Tech Stack

### Backend
| Library | Purpose |
|---|---|
| `FastAPI` | Async web framework & REST API |
| `Uvicorn` | ASGI server |
| `Motor` | Async MongoDB driver |
| `InsightFace` (`buffalo_s`) | Face detection + 512-D embedding extraction |
| `ONNX Runtime` (CPU) | Inference runtime for InsightFace models |
| `Scikit-Learn` (`DBSCAN`) | Unsupervised face clustering |
| `OpenCV` | Image loading and preprocessing |
| `Pillow` + `pillow-heif` | Image manipulation + HEIC → JPEG conversion |
| `Pydantic Settings` | Config management via `.env` |

### Frontend
| Library | Purpose |
|---|---|
| `React 18` | UI framework |
| `Vite` | Dev server & bundler |
| `Lucide Icons` | Icon set |
| `Vanilla CSS` | Glassmorphism design system |
| `EventSource` (native) | SSE client for live progress |

### Infrastructure (Current)
| Tool | Role |
|---|---|
| `MongoDB` (local) | Document store — runs on `localhost:27017` |
| `Local disk` | File storage — `./storage/` directory |
| `Docker` | Backend containerization |
| `Vercel` | Frontend deployment target (config ready) |

---

## ⚙️ Configuration

The backend is configured via a `.env` file in the `backend/` directory. If no `.env` is provided, the defaults below are used:

```env
# Database — currently points to local MongoDB
MONGO_URI=mongodb://localhost:27017
DB_NAME=dumps_db

# Storage — local disk path
STORAGE_PATH=./storage

# ML tuning parameters
DBSCAN_EPS=0.35
DBSCAN_MIN_SAMPLES=3
RESCUE_THRESHOLD=0.45

# Server
HOST=0.0.0.0
PORT=8000
```

> 💡 To switch to MongoDB Atlas, simply replace `MONGO_URI` with your Atlas SRV connection string — no code changes required.

---

## 🚀 Getting Started (Local)

### Prerequisites

- Python 3.10+
- Node.js 18+
- MongoDB running locally at `mongodb://localhost:27017`
  - Install: [mongodb.com/try/download/community](https://www.mongodb.com/try/download/community)

### 1. Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv venv

# Windows PowerShell
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Start the FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

> **Note:** On first startup, InsightFace will automatically download the `buffalo_s` model weights (~150 MB) to `~/.insightface/models/`. This only happens once.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 🐳 Docker (Backend)

```bash
cd backend
docker build -t dumps-backend .
docker run -p 8000:8000 \
  -e MONGO_URI=mongodb://host.docker.internal:27017 \
  dumps-backend
```

---

## 📁 Project Structure

```
dumps/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py               # FastAPI app setup, lifespan, CORS, mounts
│       ├── config.py             # Pydantic settings (reads from .env)
│       ├── database.py           # Motor async MongoDB connection manager
│       ├── models/               # Pydantic data models
│       ├── routers/
│       │   ├── uploads.py        # POST /api/uploads — ingest & convert photos
│       │   ├── jobs.py           # POST start job, GET SSE stream
│       │   └── clusters.py       # GET results, gallery, zip download
│       ├── services/
│       │   ├── face_pipeline.py  # The 4-stage ML pipeline (core logic)
│       │   ├── storage.py        # Disk storage abstraction (S3-ready)
│       │   └── zip_service.py    # In-memory zip archive creation
│       └── workers/
│           └── process_job.py    # Async background task + SSE broadcasting
├── frontend/
│   ├── index.html
│   ├── vite.config.js
│   ├── vercel.json               # Vercel deployment config (ready)
│   └── src/
│       ├── App.jsx               # Root component & UI state machine
│       ├── index.css             # Glassmorphism design system
│       ├── main.jsx
│       ├── components/
│       │   ├── Header.jsx
│       │   ├── UploadZone.jsx    # Drag-and-drop / folder picker
│       │   ├── ProgressBar.jsx   # Live SSE progress display
│       │   ├── PersonGrid.jsx    # Grid of detected person cards
│       │   ├── PersonTile.jsx    # Individual person card
│       │   ├── PhotoGallery.jsx  # Modal gallery for a cluster
│       │   └── ThreeDotMenu.jsx  # Per-tile context menu
│       ├── hooks/
│       │   └── useSSE.js         # SSE hook (EventSource lifecycle)
│       └── lib/
│           └── api.js            # API client functions
├── memory-measure.py             # Utility: profile InsightFace RAM at startup
└── README.md
```

---

## 🔌 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/uploads` | Upload a folder of photos |
| `POST` | `/api/jobs/{upload_id}/start` | Start face clustering job |
| `GET` | `/api/jobs/{job_id}/stream` | SSE stream for live progress |
| `GET` | `/api/clusters/{job_id}` | Get cluster results for a job |
| `GET` | `/api/clusters/{job_id}/{cluster_id}/photos` | Get photos in a cluster |
| `GET` | `/api/clusters/{job_id}/{cluster_id}/zip` | Download cluster as zip |

---

## 🧪 Memory Profiling

The included `memory-measure.py` utility profiles how much RAM InsightFace consumes at startup — useful for planning deployment on memory-constrained hosts (e.g., Render free tier: 512 MB).

```bash
pip install psutil insightface onnxruntime
python memory-measure.py
```

---

## 🚧 Current Limitations

- **Local MongoDB only:** The app connects to `mongodb://localhost:27017` by default. There is no cloud database configured yet.
- **Local disk storage:** Uploaded photos and thumbnails are stored in the `./storage/` directory on the server. There is no cloud object storage (S3/R2) configured yet.
- **CPU-only inference:** The pipeline uses `CPUExecutionProvider`. Processing large batches (300+ photos) will be slow on CPU. GPU support requires swapping to `CUDAExecutionProvider`.
- **No user authentication:** A `DEFAULT_USER_ID` placeholder is used. All uploads share the same namespace — not suitable for multi-user production use yet.
- **No 24-hour cleanup job:** The privacy-first auto-expiry policy is described in the UI but the background cleanup cron/task is not yet implemented.

---

## 🔭 Future Scope

These are the planned next steps to take DUMPS from a local prototype to a production-ready, cloud-deployed application:

### 1. 🗄️ MongoDB Atlas Migration
- Replace `MONGO_URI=mongodb://localhost:27017` with a **MongoDB Atlas SRV connection string**
- Use Atlas's free tier (M0) for development, scale to M10+ for production
- Enable Atlas **TTL indexes** on the `uploads` collection to auto-expire documents after 24 hours (replacing the manual cleanup policy)
- No code changes required — only a `.env` update, since the Motor driver supports Atlas SRV out of the box

```env
# Future: swap this one line for cloud DB
MONGO_URI=mongodb+srv://<user>:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
```

### 2. ☁️ Cloud Storage (S3 / Cloudflare R2)
- Replace the local `./storage/` directory with **AWS S3** or **Cloudflare R2**
- The `storage_service` abstraction in `services/storage.py` is already designed for this swap
- Generate pre-signed URLs for photo serving instead of mounting a static directory

### 3. 🚀 Full Cloud Deployment
- **Backend:** Deploy the Dockerized FastAPI backend to [Render](https://render.com) or [Railway](https://railway.app)
  - The `Dockerfile` and dynamic `PORT` env var support are already in place
  - Attach MongoDB Atlas as the database
- **Frontend:** Deploy the React/Vite app to [Vercel](https://vercel.com)
  - `vercel.json` is already configured in the `frontend/` directory
  - Update the API base URL to point to the deployed backend

### 4. 🔐 User Authentication
- Add JWT-based auth (e.g., using `fastapi-users` or Auth0)
- Replace `DEFAULT_USER_ID` with real per-user namespacing so uploads are isolated

### 5. ⏰ Automated 24-Hour Cleanup
- Implement the auto-expiry policy that is currently only mentioned in the UI footer
- Options: Atlas TTL index (database-level) + a scheduled cleanup worker (application-level) to delete the corresponding files from storage

### 6. ⚡ GPU Inference (Optional)
- Switch `CPUExecutionProvider` → `CUDAExecutionProvider` in `face_pipeline.py`
- Deploy on a GPU-enabled host for dramatically faster processing of large photo batches

---

## 📝 Notes

- **DBSCAN sensitivity:** Very small photo batches (< 3 similar faces) may result in all faces landing in "Unsorted". Tune `DBSCAN_MIN_SAMPLES` for smaller sets.
- **InsightFace model:** The project uses `buffalo_s` (smaller/faster) rather than `buffalo_l` (larger/more accurate). Switch in `face_pipeline.py` for better accuracy at the cost of more RAM and slower inference.

---

## 📄 License

This project is open-source under the **MIT License**.

> Model weights provided by InsightFace are licensed for **non-commercial research and educational use** only. See [InsightFace License](https://github.com/deepinsight/insightface/blob/master/LICENSE) for details.
