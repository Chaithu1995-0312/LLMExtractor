import json
import os
from typing import Dict, Optional
from nexus.config import DATA_DIR

class BrickStore:
    def __init__(self, bricks_dir: str = None):
        if bricks_dir is None:
            # Default to data/bricks if it exists, or follow old pattern relative to output
            # Actually, per target structure, data/ should have fixtures and index.
            # Bricks are generated in output/nexus/bricks.
            bricks_dir = os.path.join(os.path.dirname(DATA_DIR), "output", "nexus", "bricks")
        
        self.bricks_dir = bricks_dir
        self.metadata_store = {}
        self._load_all_bricks_metadata()

    def _load_all_bricks_metadata(self):
        # In a real system, this would load metadata more robustly
        # For now, it's a simple mock based on expected brick file structure
        if not os.path.exists(self.bricks_dir):
            return

        for root, _, files in os.walk(self.bricks_dir):
            for bf in files:
                if bf.endswith(".json"):
                    path = os.path.join(root, bf)
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            bricks_data = json.load(f)
                            for brick in bricks_data:
                                self.metadata_store[brick["brick_id"]] = {
                                    "source_file": brick["source_file"],
                                    "source_span": brick["source_span"],
                                    "file_path": path
                                }
                    except Exception:
                        continue

    def get_brick_metadata(self, brick_id: str) -> Optional[Dict]:
        return self.metadata_store.get(brick_id)

    def get_brick_text(self, brick_id: str) -> Optional[str]:
        """
        Retrieves the raw text content of a brick.
        Used for reranking.
        """
        meta = self.get_brick_metadata(brick_id)
        if not meta or "file_path" not in meta:
            return None
        
        try:
            # Efficiently read the specific brick content
            # In a production DB this would be a SELECT
            with open(meta["file_path"], "r", encoding="utf-8") as f:
                bricks_data = json.load(f)
                for brick in bricks_data:
                    if brick["brick_id"] == brick_id:
                        return brick.get("content")
        except Exception:
            return None
        return None
