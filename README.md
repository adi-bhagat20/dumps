# 📸 DUMPS — Auto-Sort Photo Dumps by Person

> **Drop in a chaotic folder of event photos. Get back per-person collections, each downloadable as a zip — zero manual tagging required.**

DUMPS is a full-stack AI-powered web application built for events, weddings, and group shoots. It uses face detection and unsupervised clustering to automatically separate a mixed folder of photos into one sub-collection per person — with live progress updates and instant zip downloads.

> ⚡ **Current Status:** Both the database and photo storage are fully migrated to the cloud! Metadata runs on **MongoDB Atlas (Cloud M0)**, and photos/thumbnails are stored in **Cloudflare R2** with pre-signed URLs, local caching, and $0 egress fees.

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
┌──────▼───────────┐   ┌──────▼───────────┐
│  MongoDB Atlas   │   │  Cloudflare R2   │
│  (Motor + SRV)   │   │ (Boto3 / S3 API) │
│                  │   │                  │
│ Active:          │   │ Active:          │
│ Cloud M0 Cluster │   │ dumps-photos     │
│ (AWS Mumbai)     │   │ (Zero Egress)    │
└──────────────────┘   └──────────────────┘
```

---

## 🛠️ Tech Stack

### Backend
| Library | Purpose |
|---|---|
| `FastAPI` | Async web framework & REST API |
| `Uvicorn` | ASGI server |
| `Motor` | Async MongoDB driver with `dnspython` SRV resolution |
| `Boto3` | S3-compatible client for Cloudflare R2 object storage |
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

### Infrastructure
| Tool | Role |
|---|---|
| `MongoDB Atlas` | Managed cloud document database (AWS Mumbai M0) |
| `Cloudflare R2` | Cloud object storage (10 GB free, $0 egress fees) |
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

## 🧪 Diagnostics & Profiling

### 1. MongoDB Atlas Diagnostic Tool
Verify connection, latency, authentication, and read/write permissions directly against your MongoDB Atlas cluster:

```bash
cd backend
python test_atlas.py
```

### 2. Cloudflare R2 Storage Diagnostic Tool
Verify S3-compatible API connection, bucket reachability, read/write permissions, and pre-signed URL generation:

```bash
cd backend
python test_r2.py
```

### 3. Memory Profiling
The included `memory-measure.py` utility profiles how much RAM InsightFace consumes at startup — useful for planning deployment on memory-constrained hosts (e.g., Render free tier: 512 MB).

```bash
pip install psutil insightface onnxruntime
python memory-measure.py
```

---

## ⚠️ Architectural Pitfalls & Engineering Log

All critical technical hurdles, container memory constraints (Render 512MB RAM OOM), SSL/TLS handshake fixes, and architectural decisions encountered during cloud migration are documented in detail in [PITFALLS.md](file:///d:/projects/dumps/PITFALLS.md).

---

## 🔭 Project Milestones & Future Scope

### Completed Milestones
- [x] **🗄️ MongoDB Atlas Migration:** Replaced local MongoDB with managed MongoDB Atlas SRV (`mongodb+srv://...`), complete with automated fail-fast startup ping verification and `/api/health` probing.
- [x] **☁️ Cloud Object Storage (Cloudflare R2):** Replaced local disk storage with Cloudflare R2 (S3-compatible, $0 egress fees), utilizing pre-signed URLs for edge image delivery and in-memory streaming zips.
- [x] **🚀 Cloud Backend Deployment (Render):** Dockerized backend live on Render (`https://dumps-api.onrender.com`) with pre-baked ONNX weights, single-threaded CPU memory limits, and lazy model loading.
- [x] **🌐 Frontend Cloud Deployment (Vercel):** React frontend configured with dynamic `VITE_API_BASE_URL` support for zero-config global deployment.

---

### 🔮 Future Scope & Planned Enhancements

#### 1. 👤 Role-Based Authentication & Stateful User Dashboards
* **Stateful User Experience:** Transition from the current anonymous/stateless single-session workflow to a fully persistent, stateful application.
* **User Accounts & RBAC:** Implement JWT / OAuth2 authentication (e.g., Supabase Auth or Auth0) with role-based access control (Admin, Event Organizer, Guest).
* **Personal Dashboard:** Provide an authenticated dashboard where users can view their past photo dump uploads, re-visit previously generated face clusters, download collections later, and track real-time processing jobs across multiple browser tabs and devices.
* **Isolated Multi-Tenant Namespaces:** Replace the `DEFAULT_USER_ID` placeholder with user-scoped database collections and secure R2 storage prefixes (`/users/{user_id}/uploads/{upload_id}/`).

#### 2. ⏱️ Automated 24-Hour Timeout (Photo & Metadata Auto-Deletion)
* **Programmatic Privacy Enforcement:** Back the "24-hour privacy guarantee" with automated infrastructure-level cleanup jobs.
* **Database TTL Indexing:** Create native MongoDB **Time-To-Live (TTL)** indexes on `created_at` fields (`expireAfterSeconds=86400`) to automatically purge expired jobs, upload metadata, and cluster records.
* **Cloud Object Purge:** Implement Cloudflare R2 bucket lifecycle rules or a daily scheduled worker to automatically delete expired image files and face crop thumbnails from object storage once their 24-hour window expires, preventing unnecessary storage costs.

#### 3. 🛡️ Strict Data Validation & Anti-Malware Security
* **Magic Byte File Inspection:** Move beyond trusting browser-supplied file extensions (`.jpg`, `.png`). Inspect file header magic bytes via `python-magic` or Pillow byte verification to guarantee uploaded files are genuine images.
* **Malicious Payload Prevention:** Prevent polyglot files, embedded executable scripts (e.g., SVG XSS, `.exe` disguised as `.jpg`), and malicious zip/archive bombs from being processed or stored.
* **Batch & Size Boundaries:** Enforce strict per-file size limits (e.g., max 25 MB/photo) and total batch limits (e.g., max 500 MB/upload) to guard against Denial of Service (DoS) attacks.
* **Graceful Handling of Corrupt Media:** Safely isolate corrupt, truncated, or unreadable image files without crashing the background worker pipeline.

#### 4. ⚡ GPU Inference & Asynchronous Task Queuing
* **Job Serialization:** Integrate Redis / Celery (or BullMQ) to queue multiple clustering jobs sequentially, preventing multi-user memory contention on free-tier servers.
* **GPU Acceleration:** Switch InsightFace from `CPUExecutionProvider` to `CUDAExecutionProvider` on a dedicated GPU worker instance for sub-second processing on large 500+ photo dumps.

---

## 📝 Notes

- **DBSCAN sensitivity:** Very small photo batches (< 3 similar faces) may result in all faces landing in "Unsorted". Tune `DBSCAN_MIN_SAMPLES` for smaller sets.
- **InsightFace model:** The project uses `buffalo_s` (smaller/faster) rather than `buffalo_l` (larger/more accurate). Switch in `face_pipeline.py` for better accuracy at the cost of more RAM and slower inference.

---

## 📄 License

This project is open-source under the **MIT License**.

> Model weights provided by InsightFace are licensed for **non-commercial research and educational use** only. See [InsightFace License](https://github.com/deepinsight/insightface/blob/master/LICENSE) for details.
