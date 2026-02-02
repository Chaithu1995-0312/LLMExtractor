import json
import os
import hashlib
from typing import Dict, List, Optional
from datetime import datetime, timezone

def get_utc_timestamp(ts: Optional[float]) -> str:
    if ts is None:
        return datetime.now(timezone.utc).isoformat()
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()

def find_root_nodes(mapping: Dict):
    return [
        node_id for node_id, node in mapping.items()
        if node.get("parent") is None
    ]

def dfs_paths(mapping: Dict, node_id: str, path: List[str], paths: List[List[str]]):
    node = mapping[node_id]
    new_path = path + [node_id]

    children = node.get("children", [])
    if not children:
        paths.append(new_path)
        return

    for child_id in children:
        dfs_paths(mapping, child_id, new_path, paths)

def extract_message(node_id: str, node: Dict):
    msg = node.get("message")
    if not msg or not msg.get("content"):
        return None

    parts = msg["content"].get("parts", [])
    text = "\n".join(p for p in parts if isinstance(p, str))
    
    author = msg.get("author", {})
    role = author.get("role", "unknown")
    model_name = msg.get("metadata", {}).get("model_slug", "unknown")

    return {
        "message_id": msg.get("id", node_id),
        "role": role,
        "content": text,
        "model_name": model_name,
        "created_at": get_utc_timestamp(msg.get("create_time"))
    }

def process_conversation(conv: Dict, output_dir: str):
    conv_id = conv["id"]
    title = conv.get("title") or "untitled"
    mapping = conv["mapping"]

    roots = find_root_nodes(mapping)
    all_paths = []

    for root in roots:
        dfs_paths(mapping, root, [], all_paths)

    # Output path-stable JSON
    conv_dir = os.path.join(output_dir, "trees", conv_id)
    os.makedirs(conv_dir, exist_ok=True)

    extracted_paths = []
    for idx, path in enumerate(all_paths, start=1):
        messages = []
        for node_id in path:
            msg = extract_message(node_id, mapping[node_id])
            if msg:
                messages.append(msg)

        if not messages:
            continue

        output = {
            "conversation_id": conv_id,
            "title": title,
            "tree_path_id": ">".join(path),
            "messages": messages
        }
        
        # Path-stable filename based on path hash
        path_hash = hashlib.sha256(">".join(path).encode()).hexdigest()[:16]
        filename = f"path_{path_hash}.json"
        file_path = os.path.join(conv_dir, filename)
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        extracted_paths.append(file_path)
    
    return extracted_paths

def load_conversations(path: str):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "conversations" in data:
        return data["conversations"]
    if isinstance(data, list):
        return data
    raise ValueError("Unknown conversations.json format")
