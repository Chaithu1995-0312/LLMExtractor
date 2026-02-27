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
from nexus.sync.router import TopicRouter, RouterConfig
from nexus.extract.tree_splitter import load_conversations, process_conversation

# Keep original config imports if needed, but we are moving to DB
from nexus.config import DEFAULT_OUTPUT_DIR

# ---------------------------------------------------------------------------
# ROUTER MODE CONSTANTS
# BROADCAST  — legacy: compile into every active topic (original behaviour)
# ROUTER     — new: use TopicRouter advisory layer to select topic(s) per run
# ---------------------------------------------------------------------------
ROUTER_MODE_BROADCAST = "broadcast"
ROUTER_MODE_ROUTER = "router"

def run_sync(
    input_json: str,
    output_dir: str,
    rebuild_index: bool = False,
    routing_mode: str = ROUTER_MODE_BROADCAST,
    router_config: "RouterConfig | None" = None,
):
    """
    Main sync entry point.

    Args:
        input_json:     Path to conversations JSON export.
        output_dir:     Directory for tree-split output files.
        rebuild_index:  If True, truncate all sync data first.
        routing_mode:   ROUTER_MODE_BROADCAST (default, legacy behaviour)
                        or ROUTER_MODE_ROUTER (use TopicRouter per-run).
        router_config:  Optional RouterConfig override for TopicRouter.
                        Only used when routing_mode == ROUTER_MODE_ROUTER.
    """
    setup_logging("sync")
    ts = lambda: datetime.now(timezone.utc).isoformat()
    print(f"[{ts()}] [START] Starting Deterministic Sync (rebuild={rebuild_index}, mode={routing_mode})...")

    try:
        # 1. Initialize The Vault & Compiler
        print(f"[{ts()}] [INIT] Connecting to Vault (Database)...")
        db = SyncDatabase()

        if rebuild_index:
            print(f"[{ts()}] [REBUILD] Flag detected. Truncating existing data...")
            db.truncate_sync_data()

        llm = LLMClient()
        compiler = NexusCompiler(db, llm)

        # 2. Bootstrap Topic (if empty)
        topics = db.get_all_topics()
        if not topics:
            print(f"[{ts()}] [BOOTSTRAP] No topics found. Creating default 'nexus-server-sync'...")
            default_def = {
                "scope_description": "Technical constraints, architectural decisions, and data flow rules for the Nexus Server Sync system.",
                "exclusion_criteria": [
                    "General pleasantries",
                    "Drafting or brainstorming that was explicitly rejected",
                    "UI styling details",
                ]
            }
            db.create_topic("nexus-server-sync", "Nexus Server Sync Architecture", default_def)
            topics = db.get_all_topics()

        print(f"[{ts()}] [CONFIG] Active Topics: {[t['id'] for t in topics]}")

        # 3. Initialize TopicRouter (only wired in ROUTER mode; else None)
        topic_router: "TopicRouter | None" = None
        if routing_mode == ROUTER_MODE_ROUTER:
            # GraphManager is needed for audit logging — import lazily to avoid
            # circular imports and because it requires DB connectivity.
            try:
                from nexus.graph.manager import GraphManager
                gm = GraphManager()
            except Exception as gm_err:
                print(f"[{ts()}] [WARN] GraphManager unavailable: {gm_err}. Router audit logging will be degraded.")
                gm = None

            topic_router = TopicRouter(
                db=db,
                graph_manager=gm,
                llm_client=llm,
                config=router_config,
            )
            print(f"[{ts()}] [ROUTER] TopicRouter initialised (advisory mode, LLM={'enabled' if (router_config is None or router_config.enable_llm) else 'disabled'}).")
        else:
            print(f"[{ts()}] [ROUTER] Broadcast mode — compiling into all {len(topics)} active topics.")

        # 4. Load Conversations
        print(f"[{ts()}] [LOAD] Reading conversations from {input_json}...")
        conversations = load_conversations(input_json)
        print(f"[{ts()}] [LOAD] Loaded {len(conversations)} conversations.")

        # 5. Processing Loop
        processed_count = 0
        total_bricks = 0

        for conv in conversations:
            conv_id = conv.get("id") or conv.get("conversation_id")
            title = conv.get("title", "Untitled")

            if not conv_id:
                continue

            print(f"[{ts()}] [SYNC] Processing: {title} ({conv_id})")

            tree_files = process_conversation(conv, output_dir)

            for tree_file in tree_files:
                with open(tree_file, "r", encoding="utf-8") as f:
                    tree_content = json.load(f)

                run_id = os.path.basename(tree_file).replace(".json", "")

                # B. Register Source Run in Vault (Safe Append)
                try:
                    db.register_run_safe(run_id, tree_content)
                except Exception as e:
                    print(f"[{ts()}] [SKIP] Skipping {run_id} due to validation error: {e}")
                    continue

                # C. Select topics for this run
                if routing_mode == ROUTER_MODE_ROUTER and topic_router is not None:
                    # ROUTER MODE: ask TopicRouter which topic(s) to compile into
                    selected_topic_ids = topic_router.route_run(run_id)
                    print(f"   -> [ROUTER] run={run_id} → {selected_topic_ids}")
                    # Filter to only ACTIVE topics that exist in DB
                    active_ids = {t["id"] for t in topics}
                    selected_topics = [
                        t for t in topics if t["id"] in selected_topic_ids and t["id"] in active_ids
                    ]
                    if not selected_topics:
                        # Fallback: use first active topic if router returned no valid match
                        selected_topics = topics[:1]
                        print(f"   -> [ROUTER] Fallback to first active topic: {selected_topics[0]['id']}")
                else:
                    # BROADCAST MODE (legacy): compile into ALL active topics
                    selected_topics = topics

                # D. Compile into selected topics (Incremental Boundary Guard)
                for topic in selected_topics:
                    while True:
                        new_cnt = compiler.compile_run(run_id, topic["id"])
                        total_bricks += new_cnt
                        if new_cnt > 0:
                            print(f"   -> Extracted {new_cnt} bricks for '{topic['id']}' from {run_id}")

                        run_state = db.get_run(run_id)
                        last_idx = run_state.get("last_processed_index", -1)
                        total_msgs = len(run_state.get("raw_content", {}).get("messages", []))

                        if last_idx >= total_msgs - 1:
                            break  # Fully processed

                        print(f"   -> Continuing compilation for '{topic['id']}' (batch completed)...")

            processed_count += 1

        print(f"[{ts()}] [COMPLETE] Processed {processed_count} conversations.")
        print(f"[{ts()}] [COMPLETE] Total Bricks Extracted: {total_bricks}")
        print(f"[{ts()}] [AUDIT] Sync completed successfully (mode={routing_mode}).")

    except Exception as e:
        print(f"[{datetime.now(timezone.utc).isoformat()}] ERROR: Sync aborted: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
