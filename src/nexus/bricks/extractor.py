import json
import os
import hashlib
from typing import List, Dict, Optional
from datetime import datetime, timezone
from unstructured.partition.auto import partition
from unstructured.cleaners.core import clean, clean_extra_whitespace, group_broken_paragraphs

def generate_brick_id(source_file: str, content: str, index: int) -> str:
    """Generate a unique, stable brick ID."""
    seed = f"{source_file}:{index}:{content}"
    return hashlib.sha256(seed.encode()).hexdigest()[:32]

def extract_bricks_from_file(tree_file_path: str, output_dir: str):
    """
    Extract atomic bricks from a tree path file using Block-Aware Semantic Distillation.
    Goal: No summaries, only atomic units with structural integrity (code/tools).
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] [BRICKS] Extracting from {os.path.basename(tree_file_path)}")
    # 1. Load raw data
    with open(tree_file_path, "r", encoding="utf-8") as f:
        tree_data = json.load(f)

    bricks = []
    
    # We iterate over messages in the tree path
    for msg in tree_data.get("messages", []):
        content_blocks = msg.get("content_blocks")
        
        if content_blocks:
            # NEW: Block-Aware Processing
            for b_idx, block in enumerate(content_blocks):
                b_type = block.get("type", "text")
                b_val = block.get("value", "")
                
                if not b_val:
                    continue

                if b_type == "text":
                    # For text blocks, use semantic distillation (splitting only)
                    candidates = [c.strip() for c in b_val.split("\n\n") if c.strip()]
                    for c_idx, candidate in enumerate(candidates):
                        bricks.append(_create_brick(
                            tree_file_path, candidate, msg["message_id"], 
                            b_idx, b_type, sub_index=c_idx
                        ))
                else:
                    # For non-text blocks (code, tool_output), 1:1 mapping
                    # b_val might be a dict for tool outputs, stringify it
                    if isinstance(b_val, dict):
                        b_val = json.dumps(b_val, ensure_ascii=False)
                    
                    bricks.append(_create_brick(
                        tree_file_path, b_val, msg["message_id"], 
                        b_idx, b_type
                    ))
        else:
            # LEGACY: Fallback to concatenated content string
            content = msg.get("content", "")
            if not content.strip():
                continue

            try:
                cleaned_content = clean(content, extra_whitespace=True, dashes=True, bullets=True)
                cleaned_content = group_broken_paragraphs(cleaned_content)
                candidates = [c.strip() for c in cleaned_content.split("\n\n") if c.strip() and len(c.strip()) > 20]
            except Exception:
                candidates = [c.strip() for c in content.split("\n\n") if c.strip()]
            
            for c_idx, candidate in enumerate(candidates):
                bricks.append(_create_brick(
                    tree_file_path, candidate, msg["message_id"], 
                    0, "text", sub_index=c_idx
                ))

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

def _create_brick(file_path: str, content: str, msg_id: str, b_idx: int, b_type: str, sub_index: int = 0) -> Dict:
    """Helper to construct a standardized Brick object."""
    # Ensure stable ID even with sub-indexing
    seed = f"{os.path.basename(file_path)}:{msg_id}:{b_idx}:{sub_index}:{content}"
    brick_id = hashlib.sha256(seed.encode()).hexdigest()[:32]
    
    return {
        "brick_id": brick_id,
        "brick_kind": b_type,
        "intent": "unknown", # Compiler-owned
        "source_file": os.path.abspath(file_path),
        "source_span": {
            "message_id": msg_id,
            "block_index": b_idx,
            "block_type": b_type,
            "sub_index": sub_index,
            "text_sample": content[:50] + "..." if len(content) > 50 else content
        },
        "tags": [f"kind:{b_type}"],
        "scope": "PRIVATE",
        "status": "PENDING",
        "content": content,
        "hash": hashlib.sha256(content.encode()).hexdigest(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
