import json
import os
import hashlib
from typing import List, Dict, Optional
from unstructured.partition.auto import partition
from unstructured.cleaners.core import clean, clean_extra_whitespace, group_broken_paragraphs

def generate_brick_id(source_file: str, content: str, index: int) -> str:
    """Generate a unique, stable brick ID."""
    seed = f"{source_file}:{index}:{content}"
    return hashlib.sha256(seed.encode()).hexdigest()[:32]

def extract_bricks_from_file(tree_file_path: str, output_dir: str):
    """
    Extract atomic bricks from a tree path file using Semantic Distillation.
    Goal: No summaries, only atomic units with noise removed.
    Uses Unstructured.io to strip noise and keep context.
    """
    # 1. Load raw data to get message metadata
    with open(tree_file_path, "r", encoding="utf-8") as f:
        tree_data = json.load(f)

    bricks = []
    
    # We iterate over messages in the tree path
    for msg in tree_data.get("messages", []):
        content = msg.get("content", "")
        if not content.strip():
            continue

        # 2. Semantic Distillation via Unstructured.io
        # We treat each message as a mini-document to preserve context per message
        try:
            # Clean content before partitioning
            cleaned_content = clean(content, extra_whitespace=True, dashes=True, bullets=True)
            cleaned_content = group_broken_paragraphs(cleaned_content)
            
            # Use simple split for now as partition(text=...) has issues in this version
            blocks = [b.strip() for b in cleaned_content.split("\n\n") if b.strip() and len(b.strip()) > 20]
        except Exception as e:
            # Fallback to simple split if Unstructured fails
            print(f"Unstructured distillation failed for message {msg.get('message_id')}: {e}")
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
