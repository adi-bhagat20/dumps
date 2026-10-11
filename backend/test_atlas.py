import asyncio
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
    print(f"Warning: No .env file found at {env_path}. Using system environment variables or defaults.")

mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
db_name = os.getenv("DB_NAME", "dumps_db")

# Mask password in URI for safe printing
display_uri = mongo_uri
if "@" in display_uri:
    prefix = display_uri.split("@")[0]
    suffix = display_uri.split("@")[1]
    if ":" in prefix:
        scheme_user = prefix.rsplit(":", 1)[0]
        display_uri = f"{scheme_user}:****@{suffix}"

print("==================================================")
print(" MongoDB Atlas Connection Diagnostic Tool")
print("==================================================")
print(f"Target URI : {display_uri}")
print(f"Database   : {db_name}")
print("--------------------------------------------------")

async def test_connection():
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
    except ImportError:
        print("[FAIL] 'motor' package is not installed. Run: pip install -r requirements.txt")
        sys.exit(1)

    print("Step 1: Checking SRV DNS & Establishing Connection...")
    t0 = time.time()
    try:
        import certifi
        client = AsyncIOMotorClient(mongo_uri, serverSelectionTimeoutMS=8000, tlsCAFile=certifi.where())
        # Force network round-trip ping
        await client.admin.command("ping")
        elapsed = (time.time() - t0) * 1000
        print(f"   [PASS] Ping successful! (Latency: {elapsed:.1f}ms)")
    except Exception as e:
        err_msg = str(e)
        print(f"   [FAIL] Connection failed: {err_msg}\n")
        print("Diagnostic Hints:")
        if "dnspython" in err_msg.lower():
            print("   -> Missing dnspython package. Run: pip install dnspython")
        elif "authentication failed" in err_msg.lower() or "bad auth" in err_msg.lower():
            print("   -> Authentication failed. Check your Atlas username and password.")
            print("   -> If your password contains special characters (like @, :, /, #), URL-encode them.")
        elif "serverselectiontimeouterror" in err_msg.lower() or "timed out" in err_msg.lower():
            print("   -> Connection timed out. Make sure your IP is whitelisted on MongoDB Atlas:")
            print("      Go to Atlas -> Network Access -> Add IP Address -> '0.0.0.0/0' (Allow Access from Anywhere).")
        sys.exit(1)

    print("\nStep 2: Testing Read/Write Permissions...")
    try:
        db = client[db_name]
        test_col = db["__atlas_test_connection__"]
        
        # Write
        test_doc = {"test": True, "created_at": time.time(), "message": "Atlas check"}
        insert_res = await test_col.insert_one(test_doc)
        print(f"   [PASS] Inserted test document (ID: {insert_res.inserted_id})")

        # Read
        found = await test_col.find_one({"_id": insert_res.inserted_id})
        assert found is not None, "Failed to read back document"
        print("   [PASS] Read test document successfully.")

        # Cleanup
        await test_col.delete_one({"_id": insert_res.inserted_id})
        print("   [PASS] Cleaned up test document.")
    except Exception as e:
        print(f"   [FAIL] Read/Write test failed: {e}")
        print("   -> Verify that your database user has 'readWriteAnyDatabase' or read/write permissions on this database.")
        sys.exit(1)
    finally:
        client.close()

    print("--------------------------------------------------")
    print("ALL CHECKS PASSED: MongoDB Atlas is ready for DUMPS!")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(test_connection())
