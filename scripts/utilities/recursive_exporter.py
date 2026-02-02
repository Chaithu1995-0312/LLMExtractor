import json
import os
import re
from datetime import datetime, timezone

# CONFIGURATION
OUTPUT_DIR = 'my_chatgpt_history'

def find_conversations_json():
    """Searches current and all child directories for 'conversations.json'."""
    for root, dirs, files in os.walk(os.getcwd()):
        if 'conversations.json' in files:
            return os.path.join(root, 'conversations.json')
    return None

def sanitize_filename(title):
    if not title: return "Untitled_Chat"
    clean = re.sub(r'[\\/*?:"<>|]', "", title)
    return clean.strip().replace(" ", "_")[:120]

def iso_utc_from_ts(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

def iso_utc_now() -> str:
    return datetime.now(tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

def get_conversation_model(mapping: dict) -> str:
    for node in mapping.values():
        msg = node.get('message')
        if not msg:
            continue
        meta = msg.get('metadata', {}) or {}
        model = meta.get('model_slug') or meta.get('model')
        if model:
            return model
    return "unknown"

def build_yaml_front_matter(conversation_id: str, model: str,
                            created_at_utc: str, exported_at_utc: str) -> str:
    return (
        "---\n"
        f"conversation_id: {conversation_id}\n"
        f"model: {model}\n"
        f"created_at_utc: {created_at_utc}\n"
        f"exported_at_utc: {exported_at_utc}\n"
        "---\n\n"
    )

def extract_text(mapping):
    """Extracts only text-based messages in chronological order."""
    messages = []
    # Sort nodes by time to keep the conversation flow correct
    nodes = sorted(mapping.values(), key=lambda x: (x.get('message') or {}).get('create_time') or 0)
    
    for node in nodes:
        msg = node.get('message')
        if msg and msg.get('content') and msg['content'].get('content_type') == 'text':
            role = msg['author']['role'].capitalize()
            parts = msg['content'].get('parts', [])
            text = "\n".join([str(p) for p in parts if isinstance(p, str)])
            
            if text.strip():
                messages.append(f"## {role}\n\n{text}\n\n---\n")
    return "\n".join(messages)

def main():
    target_file = find_conversations_json()
    
    if not target_file:
        print("❌ Error: Could not find 'conversations.json' in this folder or any subfolders.")
        print("Make sure you unzipped the export file first!")
        return

    print(f"✅ Found file at: {target_file}")
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    with open(target_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Processing {len(data)} conversations...")

    count = 0
    for chat in data:
        title = chat.get('title') or "Untitled"
        timestamp = int(chat.get('create_time', 0))
        date_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
        
        content = extract_text(chat.get('mapping', {}))
        if not content.strip():
            continue

        filename = f"{date_str}_{sanitize_filename(title)}_{timestamp}.md"

        conversation_id = chat.get('id') or chat.get('conversation_id') or "unknown"
        created_at_utc = iso_utc_from_ts(int(chat.get('create_time', 0)))
        exported_at_utc = iso_utc_now()
        model = get_conversation_model(chat.get('mapping', {}))

        yaml_block = build_yaml_front_matter(
            conversation_id=conversation_id,
            model=model,
            created_at_utc=created_at_utc,
            exported_at_utc=exported_at_utc
        )

        with open(os.path.join(OUTPUT_DIR, filename), 'w', encoding='utf-8') as f:
            f.write(yaml_block)
            f.write(f"# {title}\n*Created: {date_str}*\n\n{content}")
        count += 1

    print(f"✨ Success! {count} markdown files created in '{OUTPUT_DIR}'.")

if __name__ == "__main__":
    main()