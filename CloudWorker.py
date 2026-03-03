import os
import sys
import time
import subprocess
import psycopg2
from urllib.parse import urlparse
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    # Prioritize DATABASE_URL if present
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        result = urlparse(db_url)
        return psycopg2.connect(
            dbname=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port
        )
    
    # Fallback to individual vars
    return psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB", "nexus"),
        user=os.getenv("POSTGRES_USER", "nexus"),
        password=os.getenv("POSTGRES_PASSWORD", "nexus"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432")
    )

def process_l1_batches():
    """
    Looks for JSON batches in openaiconversations/ and processes them sequentially.
    """
    batch_dir = "openaiconversations"
    if not os.path.exists(batch_dir):
        return

    batches = sorted([f for f in os.listdir(batch_dir) if f.endswith(".json")])
    if not batches:
        return

    print(f"Found {len(batches)} batches in L1 queue.")
    print("L1 Processing: Use scripts/test_cloud_l1.py to simulate extraction.")

def process_l2_synthesis():
    """
    Triggers L2 backfill for nodes that are L1_COMPLETE but not yet synthesized.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM graph.nodes WHERE status = 'L1_COMPLETE'")
        pending = cur.fetchone()[0]
        
        if pending > 0:
            print(f"Detected {pending} nodes ready for L2 Synthesis. Triggering backfill...")
            # Use sys.executable to ensure we use the same venv
            subprocess.run([sys.executable, "scripts/run_l2_backfill.py"], check=True)
        else:
            print("No L2 pending work.")
    finally:
        cur.close()
        conn.close()

def process_l3_clustering():
    """
    Triggers L3 clustering for bricks that are L2_COMPLETE but not yet clustered.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM sync.bricks WHERE status = 'L2_COMPLETE'")
        pending = cur.fetchone()[0]
        
        if pending > 0:
            print(f"Detected {pending} bricks ready for L3 Clustering. Triggering...")
            # Use sys.executable to ensure we use the same venv
            subprocess.run([sys.executable, "scripts/run_l3_clustering.py"], check=True)
        else:
            print("No L3 pending work.")
    finally:
        cur.close()
        conn.close()

def run_tier_logic(single_run=False):
    """
    State-driven orchestrator that checks for pending work in each cognitive tier.
    """
    while True:
        try:
            print(f"\n[{datetime.now(timezone.utc).isoformat()}] --- Starting State Check Cycle ---")
            
            # 1. Tier L1: Check for new Batch Files
            process_l1_batches()
            
            # 2. Tier L2: Check for L1_COMPLETE nodes
            process_l2_synthesis()
            
            # 3. Tier L3: Check for L2_COMPLETE bricks
            process_l3_clustering()
            
            print(f"[{datetime.now(timezone.utc).isoformat()}] --- Cycle Complete. ---")
            
            if single_run:
                print("Single run requested. Exiting.")
                break

            print("Sleeping for 60s...")
            time.sleep(60)
            
        except Exception as e:
            print(f"Critical error in CloudWorker: {e}")
            if single_run: break
            time.sleep(10)

if __name__ == "__main__":
    single = "--single-run" in sys.argv
    run_tier_logic(single_run=single)
