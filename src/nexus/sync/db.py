import sqlite3
import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from nexus.config import GRAPH_DB_PATH, SYNC_SCHEMA_PATH

class SyncDatabase:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or GRAPH_DB_PATH
        self._init_db()

    def _init_db(self):
        """Initialize the database with the schema."""
        conn = self._get_conn()
        try:
            with open(SYNC_SCHEMA_PATH, "r", encoding="utf-8") as f:
                schema_sql = f.read()
            conn.executescript(schema_sql)
            conn.commit()
        except Exception as e:
            print(f"[SyncDB] Error initializing database: {e}")
        finally:
            conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    # --- TOPICS ---

    def create_topic(self, topic_id: str, display_name: str, definition: Dict, ordering_rule: str = "chronological"):
        conn = self._get_conn()
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO topics (id, display_name, definition_json, ordering_rule, state)
                VALUES (?, ?, ?, ?, 'ACTIVE')
                """,
                (topic_id, display_name, json.dumps(definition), ordering_rule)
            )
            conn.commit()
        finally:
            conn.close()

    def get_topic(self, topic_id: str) -> Optional[Dict]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT id, display_name, definition_json, ordering_rule, state FROM topics WHERE id = ?", (topic_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "id": row[0],
                "display_name": row[1],
                "definition": json.loads(row[2]),
                "ordering_rule": row[3],
                "state": row[4]
            }
        return None
    
    def get_all_topics(self) -> List[Dict]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT id, display_name, definition_json, ordering_rule, state FROM topics")
        rows = cursor.fetchall()
        conn.close()
        
        return [{
            "id": row[0],
            "display_name": row[1],
            "definition": json.loads(row[2]),
            "ordering_rule": row[3],
            "state": row[4]
        } for row in rows]

    # --- SOURCE RUNS ---

    def register_run(self, run_id: str, raw_content: Any):
        conn = self._get_conn()
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO source_runs (id, raw_content, status)
                VALUES (?, ?, 'CLOSED')
                """,
                (run_id, json.dumps(raw_content))
            )
            conn.commit()
        finally:
            conn.close()

    def get_run(self, run_id: str) -> Optional[Dict]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT id, raw_content, status, last_processed_index FROM source_runs WHERE id = ?", (run_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "id": row[0],
                "raw_content": json.loads(row[1]),
                "status": row[2],
                "last_processed_index": row[3]
            }
        return None

    def update_run_boundary(self, run_id: str, last_index: int):
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE source_runs SET last_processed_index = ? WHERE id = ?",
                (last_index, run_id)
            )
            conn.commit()
        finally:
            conn.close()

    # --- BRICKS ---

    def save_brick(self, brick: Dict):
        conn = self._get_conn()
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO bricks (
                    id, topic_id, content, fingerprint, state, 
                    run_id, json_path, start_index, end_index, source_checksum
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            conn.commit()
        finally:
            conn.close()

    def get_fingerprints_for_topic(self, topic_id: str) -> List[str]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT fingerprint FROM bricks WHERE topic_id = ?", (topic_id,))
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows]

    def get_bricks_for_topic(self, topic_id: str) -> List[Dict]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, topic_id, content, fingerprint, state, 
                   run_id, json_path, start_index, end_index, source_checksum
            FROM bricks 
            WHERE topic_id = ?
            ORDER BY created_at ASC
        """, (topic_id,))
        rows = cursor.fetchall()
        conn.close()
        
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
