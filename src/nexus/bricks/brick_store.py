import json
import os
import hashlib
from typing import Dict, Optional, List
from nexus.config import DATA_DIR
from nexus.db import get_adapter

class BrickStore:
    """
    BrickStore handles the persistence and retrieval of Bricks.
    INVARIANT: Bricks are immutable. Updates result in new versions.
    """
    def __init__(self, db_path: str = None):
        self.db = get_adapter()

    def get_brick_metadata(self, brick_id: str) -> Optional[Dict]:
        """
        Retrieves the LATEST version of brick metadata from the DB.
        """
        row = self.db.fetch_one("""
            SELECT id, type, data, created_at 
            FROM graph.nodes 
            WHERE id = %s OR id LIKE %s 
            ORDER BY created_at DESC LIMIT 1
        """, (brick_id, f"{brick_id}_v%"))

        if row:
            data = row[2] if isinstance(row[2], dict) else json.loads(row[2])
            return {
                "brick_id": row[0],
                "type": row[1],
                "created_at": row[3],
                **data
            }
        return None

    def get_brick_text(self, brick_id: str) -> Optional[str]:
        """
        Retrieves the raw text content of the latest version of a brick.
        """
        meta = self.get_brick_metadata(brick_id)
        if meta:
            return meta.get("statement") or meta.get("content")
        return None

    def save_brick(self, brick_data: Dict, actor: str = "system") -> str:
        """
        Saves a brick. If the content matches an existing brick, it returns the existing ID.
        If the ID exists but content differs, it creates a new version.
        """
        base_id = brick_data["id"]
        content = brick_data.get("content") or brick_data.get("statement")
        
        existing = self.get_brick_metadata(base_id)
        
        if existing:
            existing_content = existing.get("statement") or existing.get("content")
            if existing_content == content:
                return existing["id"] # Content matches, return existing
            
            # Content differs, create new version
            version = existing.get("version", 1)
            new_version = version + 1
            new_id = f"{base_id}_v{new_version}"
            brick_data["id"] = new_id
            brick_data["version"] = new_version
            brick_data["previous_version"] = existing["id"]
        else:
            brick_data["version"] = 1

        # Save to graph.nodes
        self.db.execute(
            "INSERT INTO graph.nodes (id, type, data, created_at) VALUES (%s, 'brick', %s, NOW())",
            (brick_data["id"], json.dumps(brick_data))
        )
        
        return brick_data["id"]

    def get_history(self, brick_id: str) -> List[Dict]:
        """
        Returns all versions of a brick, from newest to oldest.
        """
        rows = self.db.fetch_all("""
            SELECT id, data, created_at 
            FROM graph.nodes 
            WHERE id = %s OR id LIKE %s 
            ORDER BY created_at DESC
        """, (brick_id, f"{brick_id}_v%"))
        
        history = []
        for r in rows:
            data = r[1] if isinstance(r[1], dict) else json.loads(r[1])
            history.append({
                "id": r[0],
                "created_at": r[2],
                **data
            })
        return history
