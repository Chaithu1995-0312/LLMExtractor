import os
import sys
import json
from nexus.extract.tree_splitter import load_conversations, process_conversation
from nexus.bricks.extractor import extract_bricks_from_file
from nexus.walls.builder import build_walls
from nexus.vector.local_index import LocalVectorIndex
from datetime import datetime, timezone

def run_sync(input_json: str, output_dir: str):
    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting Sync...")
    
    try:
        # 1. Load Conversations
        conversations = load_conversations(input_json)
        
        # 2. Extract Trees
        all_tree_files = []
        for conv in conversations:
            tree_files = process_conversation(conv, output_dir)
            all_tree_files.extend(tree_files)
        print(f"[{datetime.now(timezone.utc).isoformat()}] EVENT: memory_extracted. {len(all_tree_files)} trees generated.")
        
        # 3. Extract Bricks
        all_bricks = []
        for tree_file in all_tree_files:
            brick_file = extract_bricks_from_file(tree_file, output_dir)
            if brick_file:
                with open(brick_file, "r", encoding="utf-8") as f:
                    all_bricks.extend(json.load(f))
        
        # 4. Build Walls
        wall_count = build_walls(all_tree_files, os.path.join(output_dir, "walls"))
        print(f"[{datetime.now(timezone.utc).isoformat()}] Walls built: {wall_count}")
        
        # 5. Vector Embedding
        index = LocalVectorIndex()
        index.add_bricks(all_bricks)
        index.save()
        print(f"[{datetime.now(timezone.utc).isoformat()}] EVENT: vector_embedded. Bricks indexed.")
        
        print(f"[{datetime.now(timezone.utc).isoformat()}] Sync Complete.")
        
    except Exception as e:
        print(f"[{datetime.now(timezone.utc).isoformat()}] ERROR: Sync aborted due to corruption/failure: {e}")
        sys.exit(1) # Fail-closed
