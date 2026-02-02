import os
import re
import json
import argparse
from math import ceil

def estimate_tokens(text):
    """
    Estimates token count using a simple heuristic: 1 token approx 4 chars.
    This avoids external dependencies like tiktoken.
    """
    return len(text) // 4

def extract_date(filename):
    """
    Extracts YYYY-MM-DD from filename.
    Returns sortable string, or fallback.
    """
    match = re.search(r"\d{4}-\d{2}-\d{2}", filename)
    return match.group(0) if match else "9999-99-99"

def main():
    parser = argparse.ArgumentParser(description="Merge markdown files into size-aware walls.")
    parser.add_argument("--input", default="my_chatgpt_history", help="Input directory containing markdown files")
    parser.add_argument("--output", default="walls", help="Output directory for walls and manifest")
    parser.add_argument("--mode", choices=["token", "char"], default="token", help="Sizing strategy: 'token' (estimated) or 'char'")
    parser.add_argument("--max-size", type=int, default=50000, help="Max size per wall (default 50000 tokens)")

    args = parser.parse_args()

    # Adjust default max size if mode is char and user didn't specify a custom max size
    # Note: If user explicitly passed 50000 but meant chars, that's small but valid.
    # However, to be helpful, if mode is char and max-size is the default 50000, we might want to increase it?
    # No, let's respect the flag. If they switch mode, they should check the size. 
    # But for safety, 50k chars is also a safe wall size, just smaller.

    if not os.path.exists(args.input):
        print(f"❌ Input folder '{args.input}' not found.")
        return

    os.makedirs(args.output, exist_ok=True)

    files = [f for f in os.listdir(args.input) if f.endswith(".md")]
    if not files:
        print("❌ No markdown files found.")
        return

    # Sort by date
    files.sort(key=extract_date)

    print(f"📄 Found {len(files)} files.")
    print(f"⚙️ Strategy: {args.mode}, Max Size: {args.max_size}")

    walls = []
    current_wall_index = 1
    current_wall_content = []
    current_wall_size = 0
    current_wall_sources = []
    
    # Manifest tracking
    manifest_walls = []

    def flush_wall():
        nonlocal current_wall_index, current_wall_content, current_wall_size, current_wall_sources
        if not current_wall_content:
            return

        filename = f"wall_{current_wall_index:03}.md"
        path = os.path.join(args.output, filename)
        
        full_content = "".join(current_wall_content)
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# WALL {current_wall_index:03}\n")
            f.write(f"_Strategy: {args.mode} based, Max: {args.max_size}_\n")
            f.write(f"_Contains {len(current_wall_sources)} conversations_\n\n")
            f.write("---\n\n")
            f.write(full_content)
            
        print(f"✅ Created {filename} (Size: {current_wall_size})")

        # Add to manifest
        total_chars = len(full_content)
        manifest_walls.append({
            "wall_id": filename,
            "total_chars": total_chars,
            "total_est_tokens": estimate_tokens(full_content),
            "sources": list(current_wall_sources)
        })

        current_wall_index += 1
        current_wall_content = []
        current_wall_size = 0
        current_wall_sources = []

    for fname in files:
        fpath = os.path.join(args.input, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()

        # Calculate size based on mode
        if args.mode == "token":
            size = estimate_tokens(content)
        else:
            size = len(content)

        # Check if adding this file exceeds limit (and we have content already)
        if current_wall_content and (current_wall_size + size > args.max_size):
            flush_wall()

        # Add file to current buffer
        # We wrap it with headers as per original logic
        entry = f"## 📄 {fname}\n\n{content}\n\n---\n\n"
        
        # Recalculate size with wrapper overhead? 
        # The prompt implies the size check is against the wall size. 
        # Let's count the actual added content size to be precise, or just the file size.
        # Counting the entry size is safer for the limit.
        if args.mode == "token":
            entry_size = estimate_tokens(entry)
        else:
            entry_size = len(entry)

        current_wall_content.append(entry)
        current_wall_size += entry_size
        current_wall_sources.append(os.path.join(args.input, fname).replace("\\", "/"))

    # Flush remaining
    flush_wall()

    # Write Manifest
    manifest_path = os.path.join(args.output, "index.json")
    manifest_data = {
        "strategy": args.mode,
        "max_size": args.max_size,
        "walls": manifest_walls
    }
    
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)
        
    print(f"\n🎉 Complete! Manifest written to {manifest_path}")

if __name__ == "__main__":
    main()
