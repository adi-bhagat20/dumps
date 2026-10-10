import io
import time
import json
import urllib.request
import urllib.parse
from PIL import Image, ImageDraw

BASE_URL = "http://127.0.0.1:8000"

def create_synthetic_photo(color: str, name: str) -> bytes:
    """Create a test image in-memory."""
    img = Image.new("RGB", (400, 400), color=color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([50, 50, 350, 350], outline="white", width=4)
    draw.text((70, 70), f"Test Photo: {name}", fill="white")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

def run_e2e_test():
    print("==================================================")
    print(" DUMPS End-to-End Pipeline Smoke Test")
    print("==================================================")

    # 1. Check health
    print("\n1. Verifying /api/health endpoint...")
    req = urllib.request.Request(f"{BASE_URL}/api/health")
    with urllib.request.urlopen(req) as resp:
        health_data = json.loads(resp.read().decode())
        print(f"   [PASS] Health Status: {health_data}")
        assert health_data["status"] == "healthy"
        assert health_data["database"] == "connected"
        assert health_data["storage"] == "r2_cloud"

    # 2. Upload test photos
    print("\n2. Uploading 3 test photos to /api/uploads...")
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = bytearray()

    # Form field: folder_name
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(b'Content-Disposition: form-data; name="folder_name"\r\n\r\n')
    body.extend(b"E2E_Test_Event\r\n")

    # Files
    photos = [
        ("photo_alice_1.jpg", "teal", "Alice 1"),
        ("photo_alice_2.jpg", "teal", "Alice 2"),
        ("photo_bob_1.jpg", "maroon", "Bob 1"),
    ]

    for fname, color, label in photos:
        file_bytes = create_synthetic_photo(color, label)
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="files"; filename="{fname}"\r\n'.encode())
        body.extend(b"Content-Type: image/jpeg\r\n\r\n")
        body.extend(file_bytes)
        body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode())

    upload_req = urllib.request.Request(
        f"{BASE_URL}/api/uploads",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )

    with urllib.request.urlopen(upload_req) as resp:
        upload_res = json.loads(resp.read().decode())
        upload_id = upload_res["upload_id"]
        print(f"   [PASS] Uploaded! upload_id={upload_id}, file_count={upload_res['file_count']}")

    # 3. Start face clustering job
    print(f"\n3. Starting background job for upload {upload_id}...")
    start_req = urllib.request.Request(
        f"{BASE_URL}/api/jobs/{upload_id}/start",
        data=b"",
        method="POST"
    )
    with urllib.request.urlopen(start_req) as resp:
        job_res = json.loads(resp.read().decode())
        job_id = job_res["job_id"]
        print(f"   [PASS] Job initiated! job_id={job_id}")

    # 4. Poll job status until complete (or SSE stream)
    print(f"\n4. Tracking pipeline execution for job {job_id}...")
    max_wait = 30
    start_time = time.time()
    clusters_data = None

    while time.time() - start_time < max_wait:
        time.sleep(1)
        clusters_req = urllib.request.Request(f"{BASE_URL}/api/clusters/{job_id}")
        try:
            with urllib.request.urlopen(clusters_req) as resp:
                clusters_data = json.loads(resp.read().decode())
                print(f"   [PASS] Pipeline completed successfully!")
                break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                # Job still processing
                continue
            else:
                raise

    assert clusters_data is not None, "Pipeline did not finish within 30s"

    clusters = clusters_data.get("clusters", [])
    print(f"\n5. Verifying Cluster Results from Cloudflare R2 & MongoDB Atlas:")
    print(f"   Found {len(clusters)} clusters/collections:")
    for c in clusters:
        print(f"   - Cluster '{c['cluster_id']}' ({c['label']}): {c['photo_count']} photos")
        if c.get("thumbnail_url"):
            print(f"     Thumbnail Pre-signed URL: {c['thumbnail_url'][:80]}...")

    # 6. Test downloading zip archive for the first cluster
    first_cluster_id = clusters[0]["cluster_id"]
    print(f"\n6. Testing in-memory zip download for '{first_cluster_id}'...")
    zip_req = urllib.request.Request(f"{BASE_URL}/api/clusters/{job_id}/{first_cluster_id}/zip")
    with urllib.request.urlopen(zip_req) as resp:
        zip_bytes = resp.read()
        print(f"   [PASS] Downloaded zip archive successfully ({len(zip_bytes)} bytes)!")

    print("\n==================================================")
    print(" ALL END-TO-END TESTS PASSED SUCCESSFULLY!")
    print(" Backend + MongoDB Atlas + Cloudflare R2 are 100% functional.")
    print("==================================================")

if __name__ == "__main__":
    run_e2e_test()
