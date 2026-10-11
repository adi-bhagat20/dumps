# ⚠️ Project Pitfalls, Architectural Challenges & Engineering Solutions

This document logs all critical architectural pitfalls, system hurdles, and security considerations encountered during the design, development, and cloud deployment of the **DUMPS** application, along with how each was solved or planned for.

---

## 1. 💾 Localhost & Ephemeral Storage Trap (Data Loss on Restart)
* **The Problem:** 
  Originally, the project relied on a local MongoDB instance (`localhost:27017`) and saved photo bytes directly into a local server directory (`./backend/storage/`). In cloud container platforms (Docker, Render, AWS), disk storage is **ephemeral** — every deployment, restart, or crash completely wiped all photos and upload metadata.
* **The Pitfall:** 
  Storing multi-megabyte image files directly in a database quickly exhausts database limits, while storing them on a local server prevents multi-server scaling and causes total data loss on restarts.
* **The Solution:** 
  - **Decoupled Architecture:** Separated metadata from binary file storage.
  - **Metadata:** Migrated to **MongoDB Atlas (Cloud M0)** with connection pooling and automated fail-fast ping verification.
  - **File Storage:** Migrated to **Cloudflare R2** (S3-compatible object storage with 10 GB free and $0 egress bandwidth charges).
  - **Pre-signed URLs:** Images and face crop thumbnails are served directly from Cloudflare's global edge network via pre-signed URLs, bypassing server load.

---

## 2. 🔒 Linux Container SSL/TLS Handshake Failures (`TLSV1_ALERT_INTERNAL_ERROR`)
* **The Problem:** 
  When deploying the backend Docker container to Linux, the application failed to boot with:
  `SSL handshake failed: [SSL: TLSV1_ALERT_INTERNAL_ERROR] tlsv1 alert internal error (_ssl.c:1010)`
* **The Pitfall:** 
  1. **Missing CA Certificates:** Minimal container base images (`python:3.12-slim`) do not package system root certificate authorities (`ca-certificates`) by default, so Python's OpenSSL could not verify MongoDB Atlas's Let's Encrypt / DigiCert certificates.
  2. **Dynamic Cloud IP Blocking:** MongoDB Atlas firewall drops connections with a TLS alert if the connecting client's IP is not whitelisted. Cloud platforms (Render) assign dynamic IP addresses that change on every deployment.
* **The Solution:**
  - Added `ca-certificates` to `apt-get install` in the [Dockerfile](file:///d:/projects/dumps/backend/Dockerfile).
  - Explicitly passed `certifi.where()` as `tlsCAFile` to the `AsyncIOMotorClient` in [database.py](file:///d:/projects/dumps/backend/app/database.py).
  - Added `0.0.0.0/0` (Allow Access from Anywhere) in MongoDB Atlas Network Access.

---

## 3. 💥 The 512MB RAM Out-Of-Memory (OOM) Crash on Cloud Hosts
* **The Problem:** 
  The backend container crashed during boot on Render with:
  `==> Out of memory (used over 512Mi)`
* **The Pitfall:** 
  1. **Runtime Download & Extraction Spike:** At startup, `InsightFace` was downloading a 125 MB zip archive, decompressing it in RAM, and initializing 5 separate ONNX models simultaneously while FastAPI was booting.
  2. **Multi-Core Host Thread Explosion:** Render runs containers on shared cloud host servers with **32 to 64 CPU cores**. By default, ONNX Runtime, OpenMP (`OMP`), and OpenBLAS inspect the host CPU count and allocate 64 threads and massive memory arenas for 64 cores, instantly exceeding 512 MB.
  3. **Unused Model Overhead:** `buffalo_s` packages 5 models (detection, recognition, 3D landmarks, 2D-106 landmarks, gender/age). The app only requires detection and recognition, but was loading all 5 into RAM.
  4. **In-Memory Multipart File Buffering:** Reading uploaded photos via `await file.read()` held full multi-megabyte image binaries in Python's heap, and `s3_client.put_object(Body=content)` buffered them again in Boto3.
  5. **Uncompressed High-Res Bitmaps in Scope:** Full-resolution 12MP–48MP smartphone photos decoded via `cv2.imread` allocated 40–80 MB raw bitmaps that lingered in scope alongside ONNX tensors during face detection.
  6. **Linux glibc Arena Allocation:** On shared 32–64 core cloud hosts, Debian's glibc creates up to 512 memory arenas (`8 * cores`), accumulating hundreds of megabytes of unreclaimed thread-local heap caches.
* **The Solution:**
  - **Bake Weights at Build Time:** Added a step in the [Dockerfile](file:///d:/projects/dumps/backend/Dockerfile) to pre-download model weights during `docker build` (where build memory is unconstrained), eliminating runtime downloads and zip decompression.
  - **Selective Model Loading:** Configured `allowed_modules=['detection', 'recognition']` in [face_pipeline.py](file:///d:/projects/dumps/backend/app/services/face_pipeline.py), cutting ONNX memory by over 60%.
  - **Strict Single-Thread & Zero-Arena Execution:** Passed custom `SessionOptions` to ONNX:
    `sess_options.intra_op_num_threads = 1`
    `sess_options.inter_op_num_threads = 1`
    `sess_options.enable_cpu_mem_arena = False`
  - **OS-Level Thread & glibc Limits:** Set `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, and `MALLOC_ARENA_MAX=2` in the Dockerfile to prevent thread pool and memory arena expansion.
  - **Lazy Loading:** Removed eager model loading from the server boot lifespan. The web server boots in under 1 second using only **~45 MB RAM**.
  - **Chunked File Streaming:** Replaced `await file.read()` with chunked disk streaming (`shutil.copyfileobj(..., length=65536)`) and `s3_client.upload_file(...)` so uploaded photos never buffer in RAM.
  - **Immediate Bitmap Disposal & Garbage Collection:** Immediately delete raw OpenCV bitmaps (`del img`) before running ONNX detection, and trigger `gc.collect()` after each processed photo to return memory to the OS.

---

## 4. 💤 Cloud Free-Tier Hibernation (Cold Starts)
* **The Problem:** 
  Free tiers on platforms like Render spin down after 15 minutes of inactivity. When the next visitor arrives, they experience a 50–60 second delay while the container wakes up.
* **The Solution:** 
  - Set up an automated ping on **cron-job.org** (or UptimeRobot) to send a lightweight `GET /api/health` request every 10 minutes.
  - Because an incoming request arrives before the 15-minute inactivity threshold, the container remains awake 24/7 with zero cold starts.

---

## 5. 🛡️ Insecure Upload Validation & Malicious File Risks (Identified Vulnerability)
* **The Current Risk:** 
  When users upload a folder, the backend currently accepts files based solely on client-provided file extensions (`.jpg`, `.png`, `.heic`). It does not verify magic bytes (file signatures) or enforce per-file upload size limits.
* **Potential Exploits:** 
  - Malicious files (scripts, executables) masquerading as images (`payload.jpg.exe` or SVG with embedded scripts).
  - Corrupted or truncated image files causing crashes inside OpenCV / PIL decoders.
  - Denial of Service (DoS) via "zip bombs" or gigabyte-sized files exhausting server memory.
* **Planned Mitigation:** 
  - Validate image magic bytes using `python-magic` or header inspection before writing to storage.
  - Strict maximum file size limits (e.g. 25 MB per image, 500 MB per batch).
  - Reject non-image MIME types at the HTTP gateway level.

---

## 6. 👤 Single-Tenant Namespace & Lack of Stateful Authentication
* **The Current Limitation:** 
  The backend currently hardcodes `DEFAULT_USER_ID = "user_v1_placeholder"`. All uploads and clustering jobs share a single namespace.
* **The Pitfall:** 
  - Users have no private session or historical gallery dashboard.
  - Anyone accessing the API could potentially view or download another user's photos if they know the `job_id`.
* **Planned Mitigation:** 
  - Implement Role-Based Access Control (RBAC) and JWT authentication (OAuth2 / Auth0 / Supabase Auth).
  - Scope all `uploads`, `jobs`, and `clusters` queries by authenticated `user_id`.
  - Provide a stateful user dashboard to view, manage, and delete past event photo collections.

---

## 7. ⏱️ Unenforced 24-Hour Expiry Policy
* **The Current Limitation:** 
  The application promises a "Privacy-First: Photos auto-expire and are deleted after 24 hours" policy in the UI, but this is not yet enforced programmatically.
* **The Pitfall:** 
  - Without automated cleanup, temporary photo dumps will accumulate indefinitely in Cloudflare R2 and MongoDB Atlas, eventually exceeding free-tier storage limits.
* **Planned Mitigation:** 
  - **Database Level:** Create native MongoDB **TTL (Time-To-Live) indexes** on the `created_at` field:
    `db.uploads.create_index("created_at", expireAfterSeconds=86400)`
  - **Storage Level:** Configure Cloudflare R2 **Object Lifecycle Rules** to automatically purge objects older than 1 day, or run a background cleanup task that calls `storage_service.delete_upload_dir(upload_id)`.

---

## 8. ⚡ CPU Inference Latency & Concurrent Job Memory Contention
* **The Problem:** 
  InsightFace inference runs via `CPUExecutionProvider` on a shared, free-tier vCPU.
* **The Pitfall:** 
  - While single-job memory is capped at ~220–280 MB, if 2 or 3 users trigger photo clustering jobs concurrently at the exact same moment on a 512 MB instance, multiple image arrays and thread buffers in memory could still risk triggering an OOM crash.
  - Processing large batches (300+ photos) takes several minutes on CPU, during which an unhandled client disconnect could leave background tasks running.
* **The Solution & Best Practices:** 
  - **Sequential / Queued Worker:** Serialize clustering tasks with an in-memory or Redis queue so only one batch processes at a time on memory-constrained tiers.
  - **Image Resizing Safeguard:** Downsample long-edge image dimensions to 640px before inference, and immediately release numpy arrays from memory.
  - **Dedicated GPU Worker:** For high-throughput production, offload face inference to a GPU-backed worker running `CUDAExecutionProvider`.

