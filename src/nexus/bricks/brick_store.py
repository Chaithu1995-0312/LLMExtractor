import json
import os
from typing import Dict, Optional
from nexus.config import DATA_DIR
from nexus.sync.db import SyncDatabase

class BrickStore:
    def __init__(self, db_path: str = None):
        self.db = SyncDatabase(db_path)
        # We can keep some caching if needed, but for now direct DB access is better for consistency.
        self.metadata_store = {} 

    def _load_all_bricks_metadata(self):
        # Deprecated: DB is the source of truth
        pass

    def get_brick_metadata(self, brick_id: str) -> Optional[Dict]:
        """
        Retrieves brick metadata from the DB.
        """
        conn = self.db._get_conn()
        c = conn.cursor()
        c.execute("""
            SELECT id, topic_id, content, run_id, json_path, start_index, end_index 
            FROM bricks WHERE id = ?
        """, (brick_id,))
        row = c.fetchone()
        conn.close()

        if row:
            return {
                "brick_id": row[0],
                "topic_id": row[1],
                # Construct legacy source info if needed by consumers
                "source_file": row[3], # Using run_id as proxy for file/source
                "source_span": {
                    "json_path": row[4],
                    "start": row[5],
                    "end": row[6]
                }
            }
        return None

    def get_brick_text(self, brick_id: str) -> Optional[str]:
        """
        Retrieves the raw text content of a brick from the DB.
        """
        conn = self.db._get_conn()
        c = conn.cursor()
        c.execute("SELECT content FROM bricks WHERE id = ?", (brick_id,))
        row = c.fetchone()
        conn.close()
        
        if row:
            return row[0]
        return None
