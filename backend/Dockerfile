FROM python:3.12-slim

# Prevent Python from writing pyc files to disk and buffering stdout/stderr
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system libraries required by OpenCV and Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download buffalo_s weights at build time so the 512MB runtime container never spikes RAM on downloads/unzipping
RUN python -c "from insightface.app import FaceAnalysis; FaceAnalysis(name='buffalo_s', allowed_modules=['detection', 'recognition'])"

# Copy application code
COPY app ./app

# Create storage folder
RUN mkdir -p storage

EXPOSE 8000

# Start Uvicorn using the PORT environment variable provided by Render (default 8000)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
