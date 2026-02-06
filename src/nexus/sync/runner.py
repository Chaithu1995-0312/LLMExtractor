import os
import sys
import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Any

from nexus.extract.tree_splitter import load_conversations, process_conversation
from nexus.bricks.extractor import extract_bricks_from_file
from nexus.walls.builder import build_walls
from nexus.vector.local_index import LocalVectorIndex
from nexus.index.conversation_index import ConversationIndex
from nexus.config import INDEX_PATH, BRICK_IDS_PATH, DEFAULT_OUTPUT_DIR

SYNC_STATE_PATH = os.path.join(DEFAULT_OUTPUT_DIR, "sync_state.json")

def _calculate_hash(content: Dict) -> str:
    """Calculate SHA256 hash of conversation content."""
    # Sort keys to ensure deterministic hash
    json_bytes = json.dumps(content, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(json_bytes).hexdigest()

def _load_sync_state() -> Dict[str, str]:
    if os.path.exists(SYNC_STATE_PATH):
        try:
            with open(SYNC_STATE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_sync_state(state: Dict[str, str]):
    os.makedirs(os.path.dirname(SYNC_STATE_PATH), exist_ok=True)
    with open(SYNC_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def run_sync(input_json: str, output_dir: str, rebuild_index: bool = False):
    print(f"[{datetime.now(timezone.utc).isoformat()}] [START] Starting Sync (rebuild_index={rebuild_index})...")
    
    try:
        # 0. Load Components
        print(f"[{datetime.now(timezone.utc).isoformat()}] [INIT] Loading sync state and indices...")
        sync_state = _load_sync_state()
        conv_index = ConversationIndex(output_dir)
        
        # 1. Load Conversations
        print(f"[{datetime.now(timezone.utc).isoformat()}] [LOAD] Reading conversations from {input_json}...")
        conversations = load_conversations(input_json)
        print(f"[{datetime.now(timezone.utc).isoformat()}] [LOAD] Loaded {len(conversations)} conversations.")

        # 2. Incremental Processing
        print(f"[{datetime.now(timezone.utc).isoformat()}] [PROCESS] Starting incremental processing...")
        processed_count = 0
        skipped_count = 0
        all_new_bricks = []
        all_tree_files = []

        if rebuild_index:
            print(f"[{datetime.now(timezone.utc).isoformat()}] Rebuild forced. Clearing sync state.")
            sync_state = {}
            # Clear vector index files
            if os.path.exists(INDEX_PATH): os.remove(INDEX_PATH)
            if os.path.exists(BRICK_IDS_PATH): os.remove(BRICK_IDS_PATH)

        for conv in conversations:
            conv_id = conv.get("id") or conv.get("conversation_id")
            title = conv.get("title", "Untitled")
            if not conv_id:
                print(f"[{datetime.now(timezone.utc).isoformat()}] [WARN] Skipping conversation without ID: {title}")
                continue
                
            current_hash = _calculate_hash(conv)
            last_hash = sync_state.get(conv_id)
            
            if last_hash == current_hash and not rebuild_index:
                skipped_count += 1
                continue

            print(f"[{datetime.now(timezone.utc).isoformat()}] [SYNC] Processing: {title} ({conv_id})")
            # Process this conversation
            try:
                # A. Extract Trees
                print(f"[{datetime.now(timezone.utc).isoformat()}] [EXTRACT] Splitting conversation into trees...")
                tree_files = process_conversation(conv, output_dir)
                all_tree_files.extend(tree_files)
                
                # B. Update Conversation Index
                # Assuming first tree file represents the conversation source or we pick one
                source_file = tree_files[0] if tree_files else ""
                conv_index.add_conversation(
                    chat_id=conv_id,
                    title=conv.get("title", "Untitled"),
                    content_hash=current_hash,
                    source_file=source_file,
                    timestamp=conv.get("create_time")
                )

                # C. Extract Bricks
                print(f"[{datetime.now(timezone.utc).isoformat()}] [BRICKS] Extracting knowledge bricks from {len(tree_files)} trees...")
                conv_bricks = []
                for tree_file in tree_files:
                    brick_file = extract_bricks_from_file(tree_file, output_dir)
                    if brick_file:
                        with open(brick_file, "r", encoding="utf-8") as f:
                            conv_bricks.extend(json.load(f))
                print(f"[{datetime.now(timezone.utc).isoformat()}] [BRICKS] Extracted {len(conv_bricks)} bricks.")
                
                # Mark new bricks as PENDING
                for b in conv_bricks:
                    b["status"] = "PENDING"
                
                all_new_bricks.extend(conv_bricks)
                
                # D. Update Sync State
                sync_state[conv_id] = current_hash
                processed_count += 1
                
            except Exception as e:
                print(f"ERROR: Failed to process conversation {conv_id}: {e}")
                # Do not update sync state so we retry next time

        # Save indices and state
        conv_index.save()
        _save_sync_state(sync_state)
        
        print(f"[{datetime.now(timezone.utc).isoformat()}] Incremental Sync: {processed_count} processed, {skipped_count} skipped.")
        
        if processed_count == 0 and not rebuild_index:
            print(f"[{datetime.now(timezone.utc).isoformat()}] No new data. Exiting.")
            return

        # 3. Build Walls (only for processed trees? Or should we rebuild walls generally? 
        # Walls might need global context, but typical logic is walls are derived from trees. 
        # For now, we only build walls from new trees to save time, or we might miss cross-linking?
        # The original code built walls from `all_tree_files`.
        # If we skipped conversations, `all_tree_files` only contains NEW trees.
        # This implies Walls are incremental or just local. 
        # Assuming Walls are local aggregations.)
        if all_tree_files:
            print(f"[{datetime.now(timezone.utc).isoformat()}] [WALLS] Building topic walls from {len(all_tree_files)} tree files...")
            wall_count = build_walls(all_tree_files, os.path.join(output_dir, "walls"))
            print(f"[{datetime.now(timezone.utc).isoformat()}] [WALLS] Success: {wall_count} walls built/updated.")
        
        # 4. Vector Embedding (only new bricks)
        if all_new_bricks:
            print(f"[{datetime.now(timezone.utc).isoformat()}] [INDEX] Embedding {len(all_new_bricks)} new bricks into vector index...")
            index = LocalVectorIndex()
            index.add_bricks(all_new_bricks)
            index.save()
            print(f"[{datetime.now(timezone.utc).isoformat()}] [INDEX] Success: Vector index updated.")
        
        print(f"[{datetime.now(timezone.utc).isoformat()}] Sync Complete.")
        
    except Exception as e:
        print(f"[{datetime.now(timezone.utc).isoformat()}] ERROR: Sync aborted due to corruption/failure: {e}")
        sys.exit(1) # Fail-closed
