import json
import os
from typing import Dict, Optional, List
from datetime import datetime, timezone
from nexus.config import DEFAULT_OUTPUT_DIR

class ConversationIndex:
    def __init__(self, output_dir: str = DEFAULT_OUTPUT_DIR):
        self.index_path = os.path.join(output_dir, "conversation_index.json")
        self.index: Dict[str, Dict] = {}
        self.load()

    def load(self):
        if os.path.exists(self.index_path):
            try:
                with open(self.index_path, "r", encoding="utf-8") as f:
                    self.index = json.load(f)
            except Exception as e:
                print(f"WARN: Failed to load conversation index: {e}")
                self.index = {}

    def save(self):
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)

    def add_conversation(self, chat_id: str, title: str, content_hash: str, source_file: str, timestamp: Optional[float] = None):
        """
        Register or update a conversation in the index.
        """
        # created_at logic
        created_at = self.index.get(chat_id, {}).get("created_at")
        if not created_at:
            created_at = timestamp if timestamp else datetime.now(timezone.utc).timestamp()
        
        updated_at = timestamp if timestamp else datetime.now(timezone.utc).timestamp()

        self.index[chat_id] = {
            "chat_id": chat_id,
            "title": title,
            "content_hash": content_hash,
            "source_file": source_file,
            "created_at": created_at,
            "updated_at": updated_at
        }

    def get_metadata(self, chat_id: str) -> Optional[Dict]:
        return self.index.get(chat_id)

    def list_conversations(self) -> List[Dict]:
        return list(self.index.values())
