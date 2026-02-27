import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from nexus.db import get_adapter
from nexus.db.init_db import init_database

class AppendViolationError(Exception):
    """Raised when an incremental update violates the append-only guarantee."""
    pass

class SyncDatabase:
    def __init__(self, db_path: str = None):
        # db_path is ignored in Postgres implementation as it uses DATABASE_URL
        self.db = get_adapter()
        self._init_db()

    def _init_db(self):
        """Initialize the database with the schema."""
        try:
            init_database()
        except Exception as e:
            print(f"[SyncDB] Error initializing database: {e}")

    # --- TOPICS ---

    def create_topic(self, topic_id: str, display_name: str, definition: Dict, ordering_rule: str = "chronological"):
        self.db.execute(
            """
            INSERT INTO sync.topics (id, display_name, definition_json, ordering_rule, state)
            VALUES (%s, %s, %s, %s, 'ACTIVE')
            ON CONFLICT (id) DO NOTHING
            """,
            (topic_id, display_name, json.dumps(definition), ordering_rule)
        )

    def get_topic(self, topic_id: str) -> Optional[Dict]:
        row = self.db.fetch_one(
            "SELECT id, display_name, definition_json, ordering_rule, state FROM sync.topics WHERE id = %s",
            (topic_id,)
        )
        
        if row:
            return {
                "id": row[0],
                "display_name": row[1],
                "definition": row[2] if isinstance(row[2], dict) else json.loads(row[2]),
                "ordering_rule": row[3],
                "state": row[4]
            }
        return None
    
    def get_all_topics(self) -> List[Dict]:
        rows = self.db.fetch_all("SELECT id, display_name, definition_json, ordering_rule, state FROM sync.topics")
        
        return [{
            "id": row[0],
            "display_name": row[1],
            "definition": row[2] if isinstance(row[2], dict) else json.loads(row[2]),
            "ordering_rule": row[3],
            "state": row[4]
        } for row in rows]

    # --- SOURCE RUNS ---

    def register_run(self, run_id: str, raw_content: Any):
        self.db.execute(
            """
            INSERT INTO sync.source_runs (id, raw_content, status)
            VALUES (%s, %s, 'CLOSED')
            ON CONFLICT (id) DO NOTHING
            """,
            (run_id, json.dumps(raw_content))
        )

    def register_run_safe(self, run_id: str, new_content: Dict):
        """
        Registers a source run with Zero-Trust Append Validation (Level 0 Hardening).
        Enforces strict byte-level prefix match to prevent history rewriting.
        """
        existing = self.get_run(run_id)
        
        if not existing:
            # New run -> Standard Insert
            print(f"[SyncDB] Registering NEW run: {run_id}")
            self.register_run(run_id, new_content)
            return

        # Append Validation
        old_msgs = existing['raw_content'].get('messages', [])
        new_msgs = new_content.get('messages', [])
        
        # Check 1: Length (Monotonicity)
        if len(new_msgs) < len(old_msgs):
            raise AppendViolationError(
                f"Regression detected for {run_id}: New length {len(new_msgs)} < Old length {len(old_msgs)}"
            )
            
        # Check 2: Strict Deep Prefix Match
        # We compare every field of the overlapping segment to ensure NO history rewrite.
        # This is stricter than just ID matching.
        for i, old_msg in enumerate(old_msgs):
            new_msg = new_msgs[i]
            
            # 2a. ID Match
            if old_msg.get('id') != new_msg.get('id'):
                raise AppendViolationError(
                    f"HISTORY_DIVERGENCE_DETECTED for {run_id} at index {i}. "
                    f"ID Mismatch: Old={old_msg.get('id')} vs New={new_msg.get('id')}"
                )
            
            # 2b. Role Match
            if old_msg.get('role') != new_msg.get('role'):
                raise AppendViolationError(
                    f"HISTORY_DIVERGENCE_DETECTED for {run_id} at index {i}. "
                    f"Role Mismatch: Old={old_msg.get('role')} vs New={new_msg.get('role')}"
                )

            # 2c. Content Match (Byte-level)
            # We strictly require the content string to be identical.
            old_content = old_msg.get('content', '')
            new_content_val = new_msg.get('content', '')
            
            # Handle list content (e.g. multimodal) by serializing first
            if isinstance(old_content, (dict, list)):
                old_content = json.dumps(old_content, sort_keys=True)
            if isinstance(new_content_val, (dict, list)):
                new_content_val = json.dumps(new_content_val, sort_keys=True)

            if old_content != new_content_val:
                raise AppendViolationError(
                    f"HISTORY_DIVERGENCE_DETECTED for {run_id} at index {i}. "
                    f"Content Mismatch! History has been rewritten."
                )

        # 3. Atomic Update
        # Update raw_content BUT keep last_processed_index
        # This effectively "extends the tape" for the compiler
        if len(new_msgs) > len(old_msgs):
            self.db.execute(
                "UPDATE sync.source_runs SET raw_content = %s WHERE id = %s",
                (json.dumps(new_content), run_id)
            )
            print(f"[SyncDB] Extended run {run_id} with {len(new_msgs) - len(old_msgs)} new messages.")
        else:
            print(f"[SyncDB] Run {run_id} is up-to-date (no new messages).")

    def get_run(self, run_id: str) -> Optional[Dict]:
        row = self.db.fetch_one(
            "SELECT id, raw_content, status, last_processed_index FROM sync.source_runs WHERE id = %s",
            (run_id,)
        )
        
        if row:
            return {
                "id": row[0],
                "raw_content": row[1] if isinstance(row[1], dict) else json.loads(row[1]),
                "status": row[2],
                "last_processed_index": row[3]
            }
        return None

    def update_run_boundary(self, run_id: str, last_index: int):
        # BOUNDARY ADVANCEMENT — FROZEN
        self.db.execute(
            "UPDATE sync.source_runs SET last_processed_index = %s WHERE id = %s",
            (last_index, run_id)
        )

    # --- BRICKS ---

    def save_brick_atomic(self, brick: Dict):
        """
        Saves a brick AND applies subsumption logic atomically in a single transaction.
        Level 0 Hardening: Ensures graph consistency even on crash.
        """
        with self.db.transaction() as cur:
            # 1. Insert/Update the new brick
            cur.execute(
                """
                INSERT INTO sync.bricks (
                    id, topic_id, content, fingerprint, state, 
                    run_id, json_path, start_index, end_index, source_checksum
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    topic_id = EXCLUDED.topic_id,
                    content = EXCLUDED.content,
                    fingerprint = EXCLUDED.fingerprint,
                    state = EXCLUDED.state,
                    run_id = EXCLUDED.run_id,
                    json_path = EXCLUDED.json_path,
                    start_index = EXCLUDED.start_index,
                    end_index = EXCLUDED.end_index,
                    source_checksum = EXCLUDED.source_checksum
                """,
                (
                    brick["id"],
                    brick["topic_id"],
                    brick["content"],
                    brick["fingerprint"],
                    brick["state"],
                    brick["source_address"]["run_id"],
                    brick["source_address"]["json_path"],
                    brick["source_address"]["indices"][0],
                    brick["source_address"]["indices"][1],
                    brick["source_address"]["checksum"]
                )
            )
            
            # 2. Sync to Unified Graph (Nodes table)
            state_map = {
                "IMPROVISE": "loose",
                "FORMING": "forming",
                "FINAL": "frozen",
                "SUPERSEDED": "killed"
            }
            node_data = {
                "statement": brick["content"],
                "lifecycle": state_map.get(brick["state"], "loose"),
                # Phase 2: Explicit lifecycle state fields.
                # vector_status: 'pending' → set to 'indexed' by index_node task.
                # drift_status:  'pending' → set to 'complete' by process_drift task.
                # Both default to 'pending' so the node is invisible to drift scans
                # until the index_node task completes and sets vector_status='indexed'.
                "vector_status": "pending",
                "drift_status": "pending",
                "metadata": {
                    "sync_topic_id": brick["topic_id"],
                    "sync_topic_name": "Nexus Server Sync Architecture", 
                    "role": brick.get("role"),
                    "authority_level": brick.get("authority_level"),
                    "message_id": brick.get("message_id")
                }
            }
            cur.execute(
                """
                INSERT INTO graph.nodes (id, type, data, created_at) 
                VALUES (%s, 'brick', %s, NOW())
                ON CONFLICT (id) DO UPDATE SET
                    data = EXCLUDED.data,
                    updated_at = NOW()
                """,
                (brick["id"], json.dumps(node_data))
            )
            
            # 3. ATOMIC SUBSUMPTION CHECK
            # We query existing bricks in the same transaction snapshot.
            # Only strictly shorter bricks can be superseded (optimization).
            # We exclude SUPERSEDED/KILLED to avoid double-tap.
            new_content = brick["content"]
            topic_id = brick["topic_id"]
            
            # Fetch candidates: same topic, active state, not self
            cur.execute("""
                SELECT id, content FROM sync.bricks 
                WHERE topic_id = %s 
                  AND state NOT IN ('SUPERSEDED', 'KILLED')
                  AND id != %s
            """, (topic_id, brick["id"]))
            
            candidates = cur.fetchall()
            
            for (old_id, old_content) in candidates:
                # Subsumption Rule: Strict Containment + Strict Length Increase
                if old_content in new_content and len(new_content) > len(old_content):
                    print(f"[SyncDB] Atomic Subsumption: {brick['id']} supersedes {old_id}")
                    
                    # 3a. Update Old Brick State
                    cur.execute(
                        """
                        UPDATE sync.bricks 
                        SET state = 'SUPERSEDED', superseded_by_id = %s 
                        WHERE id = %s
                        """,
                        (brick["id"], old_id)
                    )
                    
                    # 3b. Update Old Graph Node
                    # We have to fetch current data to modify it
                    cur.execute("SELECT data FROM graph.nodes WHERE id = %s", (old_id,))
                    row = cur.fetchone()
                    if row:
                        old_data = row[0] if isinstance(row[0], dict) else json.loads(row[0])
                        old_data["lifecycle"] = "killed"
                        old_data["superseded_by"] = brick["id"]
                        
                        cur.execute(
                            "UPDATE graph.nodes SET data = %s, updated_at = NOW() WHERE id = %s",
                            (json.dumps(old_data), old_id)
                        )
                    
                    # 3c. Create Edge
                    cur.execute(
                        """
                        INSERT INTO graph.edges (source_id, target_id, edge_type, metadata, created_at)
                        VALUES (%s, %s, 'superseded_by', '{"reason": "atomic_subsumption"}', NOW())
                        ON CONFLICT DO NOTHING
                        """,
                        (old_id, brick["id"])
                    )

            # 4. Phase 2: Enqueue index_node instead of process_drift directly.
            # New flow: Node inserted → index_node → process_drift
            # index_node is responsible for embedding + vector_status='indexed', then schedules process_drift.
            # Legacy nodes not touched by this path continue to work via existing logic.
            try:
                from services.cortex.orchestration import TaskQueue
                TaskQueue.enqueue("index_node", {"node_id": brick["id"]})
            except ImportError:
                pass
            except Exception as e:
                print(f"[SyncDB] Warning: Failed to enqueue index_node task: {e}")

    def get_fingerprints_for_topic(self, topic_id: str) -> List[str]:
        rows = self.db.fetch_all("SELECT fingerprint FROM sync.bricks WHERE topic_id = %s", (topic_id,))
        return [row[0] for row in rows]

    def get_bricks_for_topic(self, topic_id: str) -> List[Dict]:
        rows = self.db.fetch_all("""
            SELECT id, topic_id, content, fingerprint, state, 
                   run_id, json_path, start_index, end_index, source_checksum
            FROM sync.bricks 
            WHERE topic_id = %s
            ORDER BY created_at ASC
        """, (topic_id,))
        
        return [{
            "id": row[0],
            "topic_id": row[1],
            "content": row[2],
            "fingerprint": row[3],
            "state": row[4],
            "source_address": {
                "run_id": row[5],
                "json_path": row[6],
                "indices": [row[7], row[8]],
                "checksum": row[9]
            }
        } for row in rows]

    def truncate_sync_data(self):
        """Clears all bricks and resets source runs for a full rebuild."""
        try:
            with self.db.transaction() as cur:
                # Delete all bricks
                cur.execute("DELETE FROM sync.bricks")
                # Reset last_processed_index in all runs to allow re-processing
                cur.execute("UPDATE sync.source_runs SET last_processed_index = -1")
                
                # ALSO clear unified nodes to ensure the sync process actually populates them again
                cur.execute("DELETE FROM graph.nodes")
                cur.execute("DELETE FROM graph.edges")
            
            print("[SyncDB] Data truncated and runs reset for full rebuild (including unified nodes).")
        except Exception as e:
            print(f"[SyncDB] Error truncating data: {e}")
            raise

    def supersede_brick(self, old_brick_id: str, new_brick_id: str):
        """
        Marks an old brick as SUPERSEDED by a new brick.
        Also updates the corresponding graph node lifecycle.
        """
        with self.db.transaction() as cur:
            # 1. Update sync.bricks
            cur.execute(
                """
                UPDATE sync.bricks 
                SET state = 'SUPERSEDED', superseded_by_id = %s 
                WHERE id = %s
                """,
                (new_brick_id, old_brick_id)
            )
            
            # 2. Update graph.nodes (Unified Graph)
            # Fetch existing data to preserve other fields
            cur.execute("SELECT data FROM graph.nodes WHERE id = %s", (old_brick_id,))
            row = cur.fetchone()
            if row:
                data = row[0] if isinstance(row[0], dict) else json.loads(row[0])
                data["lifecycle"] = "killed" # Mapped from SUPERSEDED
                data["superseded_by"] = new_brick_id
                
                cur.execute(
                    "UPDATE graph.nodes SET data = %s, updated_at = NOW() WHERE id = %s",
                    (json.dumps(data), old_brick_id)
                )
                
            # 3. Create Edge in Graph
            # EdgeType.SUPERSEDED_BY
            cur.execute(
                """
                INSERT INTO graph.edges (source_id, target_id, edge_type, metadata, created_at)
                VALUES (%s, %s, 'superseded_by', '{"reason": "subsumption"}', NOW())
                ON CONFLICT DO NOTHING
                """,
                (old_brick_id, new_brick_id)
            )
