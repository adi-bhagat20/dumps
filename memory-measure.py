import psutil
import os

process = psutil.Process(os.getpid())

def mb():
    return process.memory_info().rss / (1024 * 1024)

print(f"Baseline (before import): {mb():.1f} MB")

from insightface.app import FaceAnalysis
print(f"After import: {mb():.1f} MB")

app = FaceAnalysis(name="buffalo_s", providers=['CPUExecutionProvider'])
print(f"After FaceAnalysis() init: {mb():.1f} MB")

app.prepare(ctx_id=-1, det_size=(640, 640))
print(f"After model.prepare() (all 5 ONNX models loaded): {mb():.1f} MB")

print(f"\n--> This number + ~80-100MB for FastAPI/uvicorn baseline")
print(f"--> is roughly what Render will need to hold at startup.")
print(f"--> Render free tier ceiling: 512 MB")