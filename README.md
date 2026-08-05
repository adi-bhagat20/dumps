# DUMPS — Auto-Sort Photo Folders by Person

**DUMPS** is a modern full-stack web application designed for events, weddings, and shared albums. Upload an unsorted folder of mixed photos and get back per-person sub-collections, each downloadable as a zip archive — with no manual tagging required.

![DUMPS UI Preview](frontend/public/preview.png)

---

## Key Features

- **Folder Upload:** Browser folder picker supporting `JPG`, `PNG`, and `HEIC` image formats.
- **HEIC Conversion:** Automatic server-side conversion of Apple `.heic` images to JPEG using `pillow-heif` before face analysis.
- **4-Stage Face Processing Pipeline:**
  1. **Detect:** Multi-face detection and 512-D embedding extraction powered by InsightFace (`buffalo_l`).
  2. **Dedupe:** Overlapping bounding box IoU filter (> 0.5) drops lower-confidence duplicate detections within the same image.
  3. **Cluster & Rescue:** DBSCAN clustering (`eps=0.35`, `min_samples=3`, metric='cosine') with centroid rescue pass for edge-case photos.
  4. **Prominent-Face Assignment:** Multi-face photos assigned to exactly one folder based on maximum bounding box area. Unclustered faces placed in an "Unsorted" collection.
- **Real-Time Progress:** Live counter ("142 / 300 photos analyzed") pushed via Server-Sent Events (SSE).
- **Per-Person Zip Download:** Instant streaming zip archive generation for any selected person or unsorted collection.
- **Privacy-First:** Auto-expiration storage model with 24-hour cleanup policy.

---

## Tech Stack

- **Frontend:** React, Vite, Lucide Icons, Glassmorphism Vanilla CSS.
- **Backend:** FastAPI, Python 3.12, Asyncio.
- **Database:** MongoDB (via Motor async driver).
- **Storage:** Local disk storage abstraction (S3/R2 ready).
- **ML / Computer Vision:** InsightFace, ONNX Runtime (CPU), OpenCV, Scikit-Learn (DBSCAN), Pillow, Pillow-HEIF.

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- MongoDB instance running locally on `mongodb://localhost:27017`

### 1. Backend Setup

```bash
cd backend
python -m venv venv
# On Windows PowerShell:
venv\Scripts\activate
# Install dependencies
pip install -r requirements.txt
# Start FastAPI backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## License

This project is open-source under the MIT License. Model weights provided by InsightFace are licensed for non-commercial research and educational use.
