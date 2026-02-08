
import sys
import os
import sqlite3
import json
import numpy as np
from datetime import datetime, timezone

# Adjust paths to import nexus modules
sys.path.append(os.path.join(os.getcwd(), "src"))

try:
    import faiss
    from nexus.config import INDEX_PATH, BRICK_IDS_PATH
    from nexus.sync.db import GRAPH_DB_PATH
    from nexus.vector.embedder import get_embedder
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

def rebuild_index():
    print(f"[{datetime.now(timezone.utc).isoformat()}] [START] Rebuilding Vector Index from DB...")
    
    # 1. Fetch all bricks from DB
    if not os.path.exists(GRAPH_DB_PATH):
        print(f"Error: Database not found at {GRAPH_DB_PATH}")
        return

    conn = sqlite3.connect(GRAPH_DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, content FROM bricks")
    rows = c.fetchall()
    conn.close()
    
    total_bricks = len(rows)
    print(f"[{datetime.now(timezone.utc).isoformat()}] [DB] Found {total_bricks} bricks in database.")
    
    if total_bricks == 0:
        print("No bricks found. Aborting.")
        return

    # 2. Reset Index Files
    # We will create a new index in memory and overwrite
    dimension = 384
    new_index = faiss.IndexFlatL2(dimension)
    new_brick_ids = []
    
    # 3. Embed in Batches
    batch_size = 64 # Use smaller batch for safety
    embedder = get_embedder()
    
    print(f"[{datetime.now(timezone.utc).isoformat()}] [EMBED] Starting embedding process...")
    
    for i in range(0, total_bricks, batch_size):
        batch = rows[i:i+batch_size]
        
        # Filter empty texts upfront to ensure alignment
        valid_batch = [(r[0], r[1]) for r in batch if r[1] and r[1].strip()]
        if not valid_batch:
            continue
            
        ids = [x[0] for x in valid_batch]
        texts = [x[1] for x in valid_batch]
        
        try:
            embeddings = embedder.embed_texts(texts)
            if len(embeddings) > 0:
                if len(embeddings) != len(ids):
                    print(f"\nWARNING: Embedding count mismatch! inputs={len(ids)}, outputs={len(embeddings)}")
                    # This should not happen if we pre-filtered, unless embedder filters more
                
                new_index.add(embeddings)
                new_brick_ids.extend(ids)
            
            # Simple progress bar
            percent = (min(i+batch_size, total_bricks) / total_bricks) * 100
            print(f"   Progress: {percent:.1f}% ({min(i+batch_size, total_bricks)}/{total_bricks})", end="\r")
        except Exception as e:
            print(f"\nError processing batch starting at {i}: {e}")
            continue

    print(f"\n[{datetime.now(timezone.utc).isoformat()}] [SAVE] Saving new index with {new_index.ntotal} vectors...")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)
    
    # Save FAISS
    faiss.write_index(new_index, INDEX_PATH)
    
    # Save IDs
    with open(BRICK_IDS_PATH, "w", encoding="utf-8") as f:
        json.dump(new_brick_ids, f)
        
    print(f"[{datetime.now(timezone.utc).isoformat()}] [SUCCESS] Index rebuild complete.")

if __name__ == "__main__":
    rebuild_index()
