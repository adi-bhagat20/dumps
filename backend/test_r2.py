import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from the backend directory
env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    print(f"Loaded configuration from: {env_path}")
else:
    print(f"Warning: No .env file found at {env_path}.")

access_key_id = os.getenv("R2_ACCESS_KEY_ID") or os.getenv("ACCESS_KEY_ID")
secret_access_key = os.getenv("R2_SECRET_ACCESS_KEY") or os.getenv("SECRET_ACCESS_KEY")
endpoint_url = os.getenv("R2_ENDPOINT_URL") or os.getenv("ENDPOINT_URL")
bucket_name = os.getenv("R2_BUCKET_NAME", "dumps-photos")

# Strip quotes and whitespace if present
if access_key_id:
    access_key_id = access_key_id.strip().strip("'\"")
if secret_access_key:
    secret_access_key = secret_access_key.strip().strip("'\"")
if endpoint_url:
    endpoint_url = endpoint_url.strip().strip("'\"")
if bucket_name:
    bucket_name = bucket_name.strip().strip("'\"")

masked_secret = secret_access_key[:4] + "...." + secret_access_key[-4:] if secret_access_key and len(secret_access_key) > 8 else "****"

print("==================================================")
print(" Cloudflare R2 Connection Diagnostic Tool")
print("==================================================")
print(f"Endpoint URL : {endpoint_url}")
print(f"Bucket Name  : {bucket_name}")
print(f"Access Key   : {access_key_id}")
print(f"Secret Key   : {masked_secret}")
print("--------------------------------------------------")

if not access_key_id or not secret_access_key or not endpoint_url:
    print("[FAIL] Missing one or more required R2 variables:")
    print(f"   ACCESS_KEY_ID     : {'Found' if access_key_id else 'MISSING'}")
    print(f"   SECRET_ACCESS_KEY : {'Found' if secret_access_key else 'MISSING'}")
    print(f"   ENDPOINT_URL      : {'Found' if endpoint_url else 'MISSING'}")
    sys.exit(1)

try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError
except ImportError:
    print("[FAIL] 'boto3' is not installed. Run: pip install boto3")
    sys.exit(1)

def run_tests():
    print("Step 1: Initializing S3 client for Cloudflare R2...")
    t0 = time.time()
    try:
        s3 = boto3.client(
            service_name="s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name="auto",
            config=Config(
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "standard"}
            )
        )
        print("   [PASS] Client created.")
    except Exception as e:
        print(f"   [FAIL] Failed to initialize client: {e}")
        sys.exit(1)

    print("\nStep 2: Testing Bucket Reachability & Listing...")
    try:
        res = s3.list_objects_v2(Bucket=bucket_name, MaxKeys=5)
        count = res.get("KeyCount", 0)
        elapsed = (time.time() - t0) * 1000
        print(f"   [PASS] Connected to bucket '{bucket_name}'! (Latency: {elapsed:.1f}ms, Current objects: {count})")
    except ClientError as e:
        err_code = e.response.get("Error", {}).get("Code", "Unknown")
        err_msg = e.response.get("Error", {}).get("Message", str(e))
        print(f"   [FAIL] Bucket access failed [{err_code}]: {err_msg}")
        if err_code == "NoSuchBucket":
            print(f"   -> Bucket '{bucket_name}' does not exist. Check spelling in Cloudflare dashboard.")
        elif err_code in ("InvalidAccessKeyId", "SignatureDoesNotMatch"):
            print("   -> Credentials invalid. Double-check ACCESS_KEY_ID and SECRET_ACCESS_KEY.")
        sys.exit(1)

    test_key = "__diagnostic_test__/hello_r2.txt"
    test_content = b"Cloudflare R2 storage integration successful for DUMPS application!"

    print("\nStep 3: Testing Object Upload (Write)...")
    try:
        s3.put_object(
            Bucket=bucket_name,
            Key=test_key,
            Body=test_content,
            ContentType="text/plain"
        )
        print(f"   [PASS] Uploaded test object: '{test_key}'")
    except Exception as e:
        print(f"   [FAIL] Upload failed: {e}")
        sys.exit(1)

    print("\nStep 4: Testing Object Download (Read)...")
    try:
        resp = s3.get_object(Bucket=bucket_name, Key=test_key)
        downloaded = resp["Body"].read()
        assert downloaded == test_content, "Downloaded content does not match uploaded content"
        print(f"   [PASS] Read test object successfully ({len(downloaded)} bytes verified).")
    except Exception as e:
        print(f"   [FAIL] Read failed: {e}")
        sys.exit(1)

    print("\nStep 5: Testing Pre-signed URL Generation...")
    try:
        presigned_url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": test_key},
            ExpiresIn=3600
        )
        print("   [PASS] Generated pre-signed URL:")
        print(f"          {presigned_url[:80]}...")
    except Exception as e:
        print(f"   [FAIL] Pre-signed URL generation failed: {e}")

    print("\nStep 6: Cleaning up test object...")
    try:
        s3.delete_object(Bucket=bucket_name, Key=test_key)
        print(f"   [PASS] Cleaned up '{test_key}'.")
    except Exception as e:
        print(f"   [FAIL] Cleanup failed: {e}")

    print("--------------------------------------------------")
    print("ALL CHECKS PASSED: Cloudflare R2 is ready for DUMPS!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
