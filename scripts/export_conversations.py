import json
import os
import re
import argparse
from datetime import datetime, timezone

# Defaults matching bulk_to_md.py
DEFAULT_INPUT = 'conversations.json'
DEFAULT_OUTPUT = 'my_chatgpt_history'
DEFAULT_CASING = 'title'
DEFAULT_FILENAME_FMT = 'title_timestamp'
DEFAULT_SANITIZE_LEN = 150
DEFAULT_HEADER_LEVEL = 2
DEFAULT_DATE_LABEL = "Created on: "
DEFAULT_JOIN_SEP = 'newline'

def sanitize_filename(name, max_length=150):
    if not name: return "Untitled_Chat"
    clean = re.sub(r'[\\/*?:"<>|]', "", name)
    return clean.strip().replace(" ", "_")[:max_length]

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

def extract_messages(mapping, role_casing='title', header_level=2, join_separator="\n"):
    chat_log = []
    # Sort keys to ensure chronological order based on create_time
    sorted_nodes = sorted(mapping.values(), key=lambda x: (x.get('message') or {}).get('create_time') or 0)
    
    for node in sorted_nodes:
        msg = node.get('message')
        if msg and msg.get('content') and msg['content'].get('content_type') == 'text':
            role = msg['author']['role']
            if role_casing.lower() == 'upper':
                role = role.upper()
            else: # Title / Capitalize
                role = role.capitalize()
            
            parts = msg['content'].get('parts', [])
            text = "\n".join([str(p) for p in parts if isinstance(p, str)])
            
            if text.strip():
                header = "#" * header_level
                chat_log.append(f"{header} {role}\n\n{text}\n\n---\n")
    
    return join_separator.join(chat_log)

def main():
    parser = argparse.ArgumentParser(description="Export ChatGPT conversations to Markdown.")
    parser.add_argument('input_file', nargs='?', default=DEFAULT_INPUT, help="Path to conversations.json")
    parser.add_argument('--out-dir', '-o', default=DEFAULT_OUTPUT, help="Output directory")
    
    # Configurable options from ticket
    parser.add_argument('--role-casing', choices=['upper', 'title'], default=DEFAULT_CASING, help="Casing for role names")
    parser.add_argument('--filename-fmt', choices=['date_title_timestamp', 'title_timestamp'], default=DEFAULT_FILENAME_FMT, help="Filename format")
    
    # Advanced options for parity
    parser.add_argument('--header-level', type=int, default=DEFAULT_HEADER_LEVEL, help="Markdown header level for roles")
    parser.add_argument('--date-label', default=DEFAULT_DATE_LABEL, help="Label for the date in the file header")
    parser.add_argument('--join-sep', choices=['newline', 'none'], default=DEFAULT_JOIN_SEP, help="Separator between messages (newline adds extra blank line)")
    parser.add_argument('--sanitize-len', type=int, default=DEFAULT_SANITIZE_LEN, help="Max filename length")

    args = parser.parse_args()

    if not os.path.exists(args.input_file):
        print(f"Error: {args.input_file} not found. Ensure it is in the correct folder.")
        return

    if not os.path.exists(args.out_dir):
        os.makedirs(args.out_dir)
        print(f"Created folder: {args.out_dir}")

    try:
        with open(args.input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading {args.input_file}: {e}")
        return

    print(f"Found {len(data)} conversations. Starting conversion...")

    count = 0
    join_char = "\n" if args.join_sep == 'newline' else ""

    for chat in data:
        title = chat.get('title') or "Untitled"
        timestamp = int(chat.get('create_time', 0))
        date_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
        
        safe_title = sanitize_filename(title, args.sanitize_len)
        
        if args.filename_fmt == 'date_title_timestamp':
            filename = f"{date_str}_{safe_title}_{timestamp}.md"
        else: # title_timestamp
            filename = f"{safe_title}_{timestamp}.md"

        content = extract_messages(chat.get('mapping', {}), 
                                   role_casing=args.role_casing, 
                                   header_level=args.header_level, 
                                   join_separator=join_char)
        
        if not content.strip():
            continue

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

        with open(os.path.join(args.out_dir, filename), 'w', encoding='utf-8') as f:
            f.write(yaml_block)
            f.write(f"# {title}\n")
            f.write(f"*{args.date_label}{date_str}*\n\n")
            f.write(content)
        
        count += 1

    print(f"Success! {count} files created in '{args.out_dir}'.")

if __name__ == "__main__":
    main()
