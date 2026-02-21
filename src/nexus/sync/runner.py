import os
import sys

# Force UTF-8 for stdout (especially for Windows compatibility)
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Any
from nexus.utils_logging import setup_logging

# Import new components
from nexus.sync.db import SyncDatabase
from nexus.sync.compiler import NexusCompiler
from nexus.sync.llm import LLMClient
from nexus.extract.tree_splitter import load_conversations, process_conversation

# Keep original config imports if needed, but we are moving to DB
from nexus.config import DEFAULT_OUTPUT_DIR

def run_sync(input_json: str, output_dir: str, rebuild_index: bool = False):
    setup_logging("sync")
    print(f"[{datetime.now(timezone.utc).isoformat()}] [START] Starting Deterministic Sync (rebuild={rebuild_index})...")
    
    try:
        # 1. Initialize The Vault & Compiler
        print(f"[{datetime.now(timezone.utc).isoformat()}] [INIT] Connecting to Vault (Database)...")
        db = SyncDatabase()

        # Handle Full Rebuild if requested
        if rebuild_index:
            print(f"[{datetime.now(timezone.utc).isoformat()}] [REBUILD] Flag detected. Truncating existing data...")
            db.truncate_sync_data()

        llm = LLMClient() # Will use env var or mock
        compiler = NexusCompiler(db, llm)

        # 2. Bootstrap Topic (if empty)
        topics = db.get_all_topics()
        if not topics:
            print(f"[{datetime.now(timezone.utc).isoformat()}] [BOOTSTRAP] No topics found. Creating default 'nexus-server-sync'...")
            default_def = {
                "scope_description": "Technical constraints, architectural decisions, and data flow rules for the Nexus Server Sync system.",
                "exclusion_criteria": [
                    "General pleasantries",
                    "Drafting or brainstorming that was explicitly rejected",
                    "UI styling details"
                ]
            }
            db.create_topic("nexus-server-sync", "Nexus Server Sync Architecture", default_def)
            topics = db.get_all_topics()
        
        print(f"[{datetime.now(timezone.utc).isoformat()}] [CONFIG] Active Topics: {[t['id'] for t in topics]}")

        # 3. Load Conversations
        print(f"[{datetime.now(timezone.utc).isoformat()}] [LOAD] Reading conversations from {input_json}...")
        conversations = load_conversations(input_json)
        print(f"[{datetime.now(timezone.utc).isoformat()}] [LOAD] Loaded {len(conversations)} conversations.")

        # 4. Processing Loop
        processed_count = 0
        total_bricks = 0
        
        for conv in conversations:
            conv_id = conv.get("id") or conv.get("conversation_id")
            title = conv.get("title", "Untitled")
            
            if not conv_id:
                continue

            print(f"[{datetime.now(timezone.utc).isoformat()}] [SYNC] Processing: {title} ({conv_id})")
            
            # A. Split into Linear Tree Paths (Source Runs)
            # process_conversation writes files to disk. We use these files as "Source Runs".
            tree_files = process_conversation(conv, output_dir)
            
            for tree_file in tree_files:
                # Load the linear transcript
                with open(tree_file, "r", encoding="utf-8") as f:
                    tree_content = json.load(f)
                
                # Generate a Run ID based on file hash or path
                # Using the filename hash part as ID is stable
                # Filename format: path_HASH.json
                run_id = os.path.basename(tree_file).replace(".json", "")
                
                # B. Register Source Run in Vault (Safe Append)
                try:
                    db.register_run_safe(run_id, tree_content)
                except Exception as e:
                    print(f"[{datetime.now(timezone.utc).isoformat()}] [SKIP] Skipping {run_id} due to validation error: {e}")
                    continue
                
                # C. Compile against ALL Active Topics
                for topic in topics:
                    # Loop compilation to handle batched processing (Incremental Boundary Guard)
                    # This ensures full processing of long conversation paths in a single sync session.
                    while True:
                        new_cnt = compiler.compile_run(run_id, topic['id'])
                        total_bricks += new_cnt
                        if new_cnt > 0:
                            print(f"   -> Extracted {new_cnt} bricks for '{topic['id']}' from {run_id}")
                        
                        # Check if more messages remain in this run
                        run_state = db.get_run(run_id)
                        last_idx = run_state.get('last_processed_index', -1)
                        total_msgs = len(run_state.get('raw_content', {}).get('messages', []))
                        
                        if last_idx >= total_msgs - 1:
                            break # Fully processed
                        
                        print(f"   -> Continuing compilation for '{topic['id']}' (batch completed)...")

            processed_count += 1

        print(f"[{datetime.now(timezone.utc).isoformat()}] [COMPLETE] Processed {processed_count} conversations.")
        print(f"[{datetime.now(timezone.utc).isoformat()}] [COMPLETE] Total Bricks Extracted: {total_bricks}")
        print(f"[{datetime.now(timezone.utc).isoformat()}] [AUDIT] Database is located at: {db.db_path}")

    except Exception as e:
        print(f"[{datetime.now(timezone.utc).isoformat()}] ERROR: Sync aborted: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
