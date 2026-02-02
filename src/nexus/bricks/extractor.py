import json
import os
import hashlib
from typing import List, Dict

def generate_brick_id(source_file: str, content: str, index: int) -> str:
    """Generate a unique, stable brick ID."""
    seed = f"{source_file}:{index}:{content}"
    return hashlib.sha256(seed.encode()).hexdigest()[:32]

def extract_bricks_from_file(tree_file_path: str, output_dir: str):
    """
    Extract atomic bricks from a tree path file.
    Goal: No summaries, only atomic units.
    One message = One or more bricks (split by double newline for now as atomic units).
    """
    with open(tree_file_path, "r", encoding="utf-8") as f:
        tree_data = json.load(f)

    bricks = []
    
    # We iterate over messages in the tree path
    for msg in tree_data.get("messages", []):
        content = msg.get("content", "")
        if not content.strip():
            continue

        # Split content into atomic paragraphs/blocks
        # Rule: One brick = one idea. For ChatGPT messages, 
        # double newlines are a good proxy for distinct ideas.
        blocks = [b.strip() for b in content.split("\n\n") if b.strip()]
        
        for idx, block in enumerate(blocks):
            brick_id = generate_brick_id(tree_file_path, block, idx)
            
            # Brick schema (LOCKED)
            brick = {
                "brick_id": brick_id,
                "source_file": os.path.abspath(tree_file_path),
                "source_span": {
                    "message_id": msg["message_id"],
                    "block_index": idx,
                    "text_sample": block[:50] + "..." if len(block) > 50 else block
                },
                "intent": "atomic_content", # Placeholder for lightweight classification if needed
                "tags": [],
                "scope": "PRIVATE", # Default
                "status": "PENDING",
                "content": block, # We store content for embedding, but reload from source in MODE-1
                "hash": hashlib.sha256(block.encode()).hexdigest()
            }
            bricks.append(brick)

    # Save bricks
    if bricks:
        bricks_dir = os.path.join(output_dir, "bricks")
        os.makedirs(bricks_dir, exist_ok=True)
        
        # Use a stable filename for the bricks derived from the source tree file
        base_name = os.path.basename(tree_file_path).replace(".json", "_bricks.json")
        parent_dir_name = os.path.basename(os.path.dirname(tree_file_path))
        conv_bricks_dir = os.path.join(bricks_dir, parent_dir_name)
        os.makedirs(conv_bricks_dir, exist_ok=True)
        
        output_path = os.path.join(conv_bricks_dir, base_name)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(bricks, f, ensure_ascii=False, indent=2)
        
        return output_path
    
    return None
