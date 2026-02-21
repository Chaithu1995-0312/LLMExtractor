import os
import json
import boto3
import psycopg2
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "dbname": os.getenv("POSTGRES_DB", "jarvis"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5432")
}

BUCKET = os.getenv("NEXUS_S3_BUCKET", "chat-bricks-bucket")
PREFIX = "nexus/runs/"

def get_latest_run_key():
    s3 = boto3.client("s3")
    try:
        response = s3.list_objects_v2(Bucket=BUCKET, Prefix=PREFIX)
        if "Contents" not in response:
            print("No runs found in S3.")
            return None
            
        latest = sorted(
            response["Contents"],
            key=lambda x: x["LastModified"],
            reverse=True
        )[0]["Key"]
        return latest
    except Exception as e:
        print(f"Error listing S3 objects: {e}")
        return None

def sync():
    key = get_latest_run_key()
    if not key:
        return

    s3 = boto3.client("s3")
    local_file = "latest_run.json"
    print(f"Downloading {key}...")
    s3.download_file(BUCKET, key, local_file)

    with open(local_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    run_id = data.get("run_id")
    pointers = data.get("extracted_pointers", [])

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    try:
        # 1. Register Run
        cur.execute("""
            INSERT INTO runs (run_id, s3_key, status, processed_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (run_id) DO UPDATE SET status = 'SYNCED'
        """, (run_id, key, 'SYNCED', datetime.now(timezone.utc)))

        # 2. Upsert Intents and Nodes
        for p in pointers:
            intent_id = p["topic_id"]

            cur.execute("""
                INSERT INTO intents (id, title, lifecycle, confidence)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET updated_at = NOW()
            """, (intent_id, intent_id.replace("-", " ").title(), "FORMING", 0.9))

            cur.execute("""
                INSERT INTO nodes (intent_id, json_path, verbatim_quote, source_run_id)
                VALUES (%s, %s, %s, %s)
            """, (
                intent_id,
                p["json_path"],
                p["verbatim_quote"],
                run_id
            ))

        conn.commit()
        print(f"Successfully synced run {run_id} with {len(pointers)} nodes.")
    except Exception as e:
        conn.rollback()
        print(f"Sync failed: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    sync()
