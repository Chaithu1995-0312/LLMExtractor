import json
import tiktoken
import os
from pathlib import Path
from src.nexus.config import COGNITIVE_SHARD_LIMIT
from src.nexus.db import get_adapter
from src.nexus.db.init_db import init_database

INPUT = "conversations.json"
MAX_TOKENS = COGNITIVE_SHARD_LIMIT

# Initialize DB connection
try:
    init_database()
except Exception as e:
    print(f"DB Init Warning: {e}")

db = get_adapter()

enc = tiktoken.get_encoding("cl100k_base")

def token_count(text):
    return len(enc.encode(text))

def serialize_msg(m):
    role = m.get("author", {}).get("role", "")
    content_obj = m.get("content", {})
    parts = content_obj.get("parts", [""])
    # Handle list of strings or list of complex objects
    content_text = ""
    for p in parts:
        if isinstance(p, str):
            content_text += p
        elif isinstance(p, dict):
            content_text += json.dumps(p)
    return f"{role}: {content_text}"

print(f"Loading {INPUT}...")
try:
    with open(INPUT, "r", encoding="utf-8") as f:
        conversations = json.load(f)
except FileNotFoundError:
    print(f"Input file {INPUT} not found. Skipping shard generation.")
    conversations = []

shard_id = 0
total_msgs_processed = 0

print(f"Processing {len(conversations)} conversations...")

# Clear existing shards? 
# The script seems to be a "full rebuild" tool.
# db.execute("DELETE FROM sync.cognitive_shards") # Safer to not delete unless requested.

for conv in conversations:
    # Conversations usually have a mapping of message IDs to message objects
    mapping = conv.get("mapping", {})
    # Sort messages by create_time if available, or just take the values
    # In some exports, the mapping is a flat dict of node IDs.
    msgs = list(mapping.values())
    
    texts = []
    for m in msgs:
        if isinstance(m, dict) and "message" in m and m["message"]:
            texts.append(serialize_msg(m["message"]))
            total_msgs_processed += 1

    buffer = []
    buffer_tokens = 0

    for t in texts:
        t_tokens = token_count(t)

        if buffer_tokens + t_tokens > MAX_TOKENS and buffer:
            shard_content = "\n".join(buffer)
            db.execute(
                "INSERT INTO sync.cognitive_shards (shard_id, text, created_at) VALUES (%s, %s, NOW())",
                (shard_id, shard_content)
            )
            shard_id += 1
            buffer = []
            buffer_tokens = 0

        buffer.append(t)
        buffer_tokens += t_tokens

    if buffer:
        shard_content = "\n".join(buffer)
        db.execute(
            "INSERT INTO sync.cognitive_shards (shard_id, text, created_at) VALUES (%s, %s, NOW())",
            (shard_id, shard_content)
        )
        shard_id += 1

print(f"Created {shard_id} cognitive shards from {total_msgs_processed} messages in Database.")
