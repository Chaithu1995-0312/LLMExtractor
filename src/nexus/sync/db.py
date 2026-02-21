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
        Registers a source run with Zero-Trust Append Validation.
        If the run exists, verifies that the new content is a strict superset (prefix match).
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
            
        # Check 2: Prefix Match (Zero-Trust ID Check)
        # We compare message_ids for the overlapping segment to ensure history hasn't been rewritten
        old_ids = [m.get('message_id') for m in old_msgs]
        new_ids_prefix = [m.get('message_id') for m in new_msgs[:len(old_msgs)]]
        
        if old_ids != new_ids_prefix:
            # Determine where it diverged for debugging
            divergence_idx = -1
            for i, (oid, nid) in enumerate(zip(old_ids, new_ids_prefix)):
                if oid != nid:
                    divergence_idx = i
                    break
            
            raise AppendViolationError(
                f"History divergence detected for {run_id} at index {divergence_idx}. "
                f"Old ID: {old_ids[divergence_idx] if divergence_idx != -1 else '?'}, "
                f"New ID: {new_ids_prefix[divergence_idx] if divergence_idx != -1 else '?'}"
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

    def save_brick(self, brick: Dict):
        with self.db.transaction() as cur:
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
            
            # Atomic update to unified nodes to ensure they are visible to external tools
            state_map = {
                "IMPROVISE": "loose",
                "FORMING": "forming",
                "FINAL": "frozen",
                "SUPERSEDED": "killed"
            }
            node_data = {
                "statement": brick["content"],
                "lifecycle": state_map.get(brick["state"], "loose"),
                "metadata": {
                    "sync_topic_id": brick["topic_id"],
                    "sync_topic_name": "Nexus Server Sync Architecture" # Fallback/Mock name
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
