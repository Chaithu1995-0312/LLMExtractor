import os
import json
import yaml
import tiktoken
from datetime import datetime, timezone
from typing import List, Dict

def get_tokenizer(model="gpt-4"):
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return tiktoken.get_encoding("cl100k_base")

def build_walls(tree_files: List[str], output_dir: str, target_size: int = 32000):
    """
    Build token-aware walls from extracted trees.
    Target sizes: 32k (default), 128k.
    Never split inside a message.
    Deterministic output.
    """
    tokenizer = get_tokenizer()
    os.makedirs(output_dir, exist_ok=True)
    
    # Sort tree files for determinism
    tree_files.sort()
    
    current_wall_id = 1
    current_wall_tokens = 0
    current_wall_content = []
    current_wall_sources = []
    
    def flush_wall(content, sources, tokens, wall_id):
        wall_filename = f"wall_{wall_id:03}.md"
        wall_path = os.path.join(output_dir, wall_filename)
        
        # YAML Frontmatter
        frontmatter = {
            "source_files": [os.path.abspath(s) for s in sources],
            "token_count": tokens,
            "created_at": "2026-01-01T00:00:00Z" # Deterministic timestamp for now, or omit from content comparison
        }
        
        with open(wall_path, "w", encoding="utf-8") as f:
            f.write("---\n")
            yaml.dump(frontmatter, f)
            f.write("---\n\n")
            f.write("\n\n---\n\n".join(content))
        
        return wall_filename

    for tree_file in tree_files:
        print(f"[{datetime.now(timezone.utc).isoformat()}] [WALLS] Adding {os.path.basename(tree_file)} to wall...")
        with open(tree_file, "r", encoding="utf-8") as f:
            tree_data = json.load(f)
        
        # Prepare conversation text for the wall
        conv_parts = []
        conv_parts.append(f"# Conversation: {tree_data.get('title', 'Untitled')}")
        conv_parts.append(f"ID: {tree_data['conversation_id']}")
        
        for msg in tree_data.get("messages", []):
            msg_text = f"### {msg['role']} ({msg['model_name']})\n{msg['content']}"
            conv_parts.append(msg_text)
        
        full_conv_text = "\n\n".join(conv_parts)
        conv_tokens = len(tokenizer.encode(full_conv_text))
        
        # If adding this conversation exceeds target_size, flush current wall
        if current_wall_content and (current_wall_tokens + conv_tokens > target_size):
            flush_wall(current_wall_content, current_wall_sources, current_wall_tokens, current_wall_id)
            current_wall_id += 1
            current_wall_content = []
            current_wall_sources = []
            current_wall_tokens = 0
            
        current_wall_content.append(full_conv_text)
        current_wall_sources.append(tree_file)
        current_wall_tokens += conv_tokens

    # Final flush
    if current_wall_content:
        flush_wall(current_wall_content, current_wall_sources, current_wall_tokens, current_wall_id)

    return current_wall_id
