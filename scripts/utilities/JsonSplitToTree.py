import json
import os
from typing import Dict, List

INPUT_FILE = "conversations.json"
OUTPUT_DIR = "output"

os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_conversations(path: str):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Export format A: { "conversations": [...] }
    if isinstance(data, dict) and "conversations" in data:
        return data["conversations"]

    # Export format B: [ {...}, {...} ]
    if isinstance(data, list):
        return data

    raise ValueError("Unknown conversations.json format")



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


def extract_message(node):
    msg = node.get("message")
    if not msg or not msg.get("content"):
        return None

    parts = msg["content"].get("parts", [])
    text = "\n".join(p for p in parts if isinstance(p, str))

    return {
        "node_id": node["id"],
        "role": msg["author"]["role"],
        "timestamp": msg.get("create_time"),
        "text": text
    }


def process_conversation(conv):
    conv_id = conv["id"]
    mapping = conv["mapping"]

    roots = find_root_nodes(mapping)
    all_paths = []

    for root in roots:
        dfs_paths(mapping, root, [], all_paths)

    conv_dir = os.path.join(OUTPUT_DIR, conv_id)
    os.makedirs(conv_dir, exist_ok=True)

    for idx, path in enumerate(all_paths, start=1):
        messages = []
        for node_id in path:
            msg = extract_message(mapping[node_id])
            if msg:
                messages.append(msg)

        output = {
            "conversation_id": conv_id,
            "tree_path_id": ">".join(path),
            "messages": messages
        }

        with open(
            os.path.join(conv_dir, f"path_{idx:03}.json"),
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(output, f, ensure_ascii=False, indent=2)


def main():
    conversations = load_conversations(INPUT_FILE)
    for conv in conversations:
        process_conversation(conv)


if __name__ == "__main__":
    main()
