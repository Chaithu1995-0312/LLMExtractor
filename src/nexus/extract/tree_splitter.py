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

def extract_message(node_id: str, node: Dict, conversation_id: str = "unknown", path_id: str = "unknown", depth: int = 0):
    msg = node.get("message")
    if not msg or not msg.get("content"):
        return None

    raw_parts = msg["content"].get("parts", [])
    content_type = msg["content"].get("content_type", "text")
    
    rich_ingest = os.getenv("NEXUS_RICH_INGEST", "false").lower() == "true"
    
    text_parts = []
    content_blocks = []
    
    for part in raw_parts:
        if isinstance(part, str):
            text_parts.append(part)
            if rich_ingest:
                block_type = "text"
                # Heuristic: if content_type is code, this part is likely code
                if content_type == "code":
                    block_type = "code"
                content_blocks.append({"type": block_type, "value": part})
        elif isinstance(part, dict) and rich_ingest:
            # Handle rich parts (tool outputs, etc.)
            part_type = part.get("type", "unknown")
            text_parts.append(f"[{part_type.upper()}]")
            content_blocks.append({"type": part_type, "value": part})
    
    text = "\n".join(text_parts)
    
    author = msg.get("author", {})
    role = author.get("role", "unknown")
    metadata = msg.get("metadata", {}) or {}
    model_name = metadata.get("model_slug", metadata.get("model", "unknown"))

    result = {
        "message_id": msg.get("id", node_id),
        "role": role,
        "content": text,
        "model_name": model_name,
        "created_at": get_utc_timestamp(msg.get("create_time"))
    }

    if rich_ingest:
        # Add additive rich fields
        result["content_blocks"] = content_blocks
        result["provenance"] = {
            "conversation_id": conversation_id,
            "mapping_id": node_id,
            "path_id": path_id,
            "branch_depth": depth
        }
        # Tiered Metadata
        result["metadata"] = {
            "tier1": {
                "content_type": content_type,
                "recipient": msg.get("recipient", "all"),
                "finish_details": metadata.get("finish_details"),
                "citations": metadata.get("citations", []),
                "update_time": get_utc_timestamp(msg.get("update_time"))
            },
            "tier2": metadata # Store raw for future-proofing
        }

    return result

def process_conversation(conv: Dict, output_dir: str):
    conv_id = conv["id"]
    title = conv.get("title") or "untitled"
    mapping = conv["mapping"]

    roots = find_root_nodes(mapping)
    all_paths = []

    for root in roots:
        dfs_paths(mapping, root, [], all_paths)

    print(f"[{datetime.now(timezone.utc).isoformat()}] [EXTRACT] Found {len(all_paths)} conversation paths.")

    # Output path-stable JSON
    conv_dir = os.path.join(output_dir, "trees", conv_id)
    os.makedirs(conv_dir, exist_ok=True)

    extracted_paths = []
    for idx, path in enumerate(all_paths, start=1):
        path_id = hashlib.sha256(">".join(path).encode()).hexdigest()[:16]
        messages = []
        for depth, node_id in enumerate(path):
            msg = extract_message(node_id, mapping[node_id], 
                                  conversation_id=conv_id, 
                                  path_id=path_id, 
                                  depth=depth)
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
