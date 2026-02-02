import json
import os
from datetime import datetime

# --- CONFIGURATION ---
SOURCE_FILE = 'conversations.json'
OUTPUT_FILE = 'nexus_prompts_library.json'

def extract_prompts():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🟢 Nexus Prompt Extractor Initialized...")
    
    # 1. Check Authority File
    if not os.path.exists(SOURCE_FILE):
        print(f"❌ Error: Source file '{SOURCE_FILE}' not found.")
        return

    # 2. Load Raw Authority (RWA)
    try:
        with open(SOURCE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📂 Loaded {len(data)} conversation threads.")
    except Exception as e:
        print(f"❌ Error reading JSON: {e}")
        return

    prompts_list = []
    
    # 3. Iterate and Extract (The Logic)
    # We scan the conversation tree for every message where role = 'user'
    for conversation in data:
        title = conversation.get('title', 'Untitled')
        mapping = conversation.get('mapping', {})
        
        for node_id, node in mapping.items():
            message = node.get('message')
            if message and message.get('author', {}).get('role') == 'user':
                
                # Extract content
                content_parts = message.get('content', {}).get('parts', [])
                full_text = "".join([str(part) for part in content_parts if isinstance(part, str)])
                
                if full_text.strip():
                    timestamp = message.get('create_time')
                    
                    # Create the Prompt Brick
                    prompt_brick = {
                        "type": "PROMPT",
                        "source_thread": title,
                        "timestamp": datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S') if timestamp else "Unknown",
                        "content": full_text
                    }
                    prompts_list.append(prompt_brick)

    # 4. Save to Structural Index
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(prompts_list, f, indent=2, ensure_ascii=False)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Success.")
    print(f"📊 Extracted {len(prompts_list)} unique prompts.")
    print(f"💾 Saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    extract_prompts()