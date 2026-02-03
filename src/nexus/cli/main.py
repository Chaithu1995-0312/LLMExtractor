import argparse
import sys
import os
import json
from datetime import datetime, timezone

from nexus.ask.recall import recall_bricks
from nexus.bricks.brick_store import BrickStore
# Cortex is now isolated, but we can still import it if it's in the python path or installed
# For now, we adjust the import to match the new structure if needed, or assume it's available.
try:
    from cortex.api import CortexAPI
except ImportError:
    # Fallback for when cortex is not installed as a package but available in services/
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "services")))
    from cortex.api import CortexAPI

_cortex_api = CortexAPI()
_brick_store = BrickStore()

def get_utc_now():
    return datetime.now(timezone.utc).isoformat()

def sanitize_filename(name, max_length=120):
    """Enforce filename sanitization (120–150 chars)"""
    # Basic sanitization: replace non-alphanumeric with underscores
    sanitized = "".join(c if c.isalnum() or c in ".-_" else "_" for c in name)
    return sanitized[:max_length]

def cmd_extract(args):
    """Subcommand: extract"""
    from nexus.extract.tree_splitter import load_conversations, process_conversation
    from nexus.bricks.extractor import extract_bricks_from_file
    
    print(f"[{get_utc_now()}] Running 'extract'...")
    if not os.path.exists(args.input):
        print(f"Error: Input path {args.input} does not exist.")
        sys.exit(1)
    
    conversations = load_conversations(args.input)
    for conv in conversations:
        tree_files = process_conversation(conv, args.output)
        for tf in tree_files:
            extract_bricks_from_file(tf, args.output)

def cmd_wall(args):
    """Subcommand: wall"""
    from nexus.walls.builder import build_walls
    import glob
    print(f"[{get_utc_now()}] Running 'wall'...")
    tree_files = glob.glob(os.path.join(args.input, "trees", "*", "*.json"))
    build_walls(tree_files, os.path.join(args.input, "walls"), target_size=args.size)

def cmd_sync(args):
    """Subcommand: sync"""
    from nexus.sync.runner import run_sync
    # Default search for conversations.json in current dir or common exports
    input_file = "conversations.json"
    output_dir = "output/nexus"
    run_sync(input_file, output_dir, rebuild_index=args.rebuild_index)

def cmd_ask(args):
    """Subcommand: ask"""
    query = args.query
    top_k = args.top_k # Default 5

    # Perform semantic recall
    recalled_bricks = recall_bricks(query, k=top_k)

    if args.json:
        results = []
        for brick in recalled_bricks:
            metadata = _brick_store.get_brick_metadata(brick["brick_id"])
            source_file = metadata.get("source_file", "") if metadata else ""
            source_span = metadata.get("source_span", "") if metadata else ""
            results.append({
                "brick_id": brick["brick_id"],
                "confidence": round(brick["confidence"], 4), # Round for consistent JSON output
                "source_file": source_file,
                "source_span": source_span
            })
        
        output = {
            "query": query,
            "timestamp": get_utc_now(),
            "results": results
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"[{get_utc_now()}] Nexus Ask Results for: \"{query}\"\n")
        if not recalled_bricks:
            print("No relevant bricks found.")
        else:
            # Pretty print for human output
            for i, brick in enumerate(recalled_bricks):
                metadata = _brick_store.get_brick_metadata(brick["brick_id"])
                source_file = metadata.get("source_file", "N/A") if metadata else "N/A"
                source_span = metadata.get("source_span", "N/A") if metadata else "N/A"
                print(f"  {i+1}. Brick ID: {brick["brick_id"]}")
                print(f"     Confidence: {brick["confidence"]:.4f}")
                print(f"     Source: {source_file} (Span: {source_span})\n")
            
            # Governed Handoff to Cortex
            print(f"[{get_utc_now()}] Handoff to Cortex for generation...")
            # Mock user_id and agent_id for now
            user_id = "nexus_cli_user"
            agent_id = "nexus_cli_agent"
            cortex_brick_ids = [b["brick_id"] for b in recalled_bricks]
            
            cortex_response = _cortex_api.generate(user_id, agent_id, query, cortex_brick_ids)
            print(f"[{get_utc_now()}] Cortex Response: {cortex_response.get("response", "Error or no response from Cortex")}")

def main():
    parser = argparse.ArgumentParser(prog="nexus", description="Nexus Productivity Backbone CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # extract
    parser_extract = subparsers.add_parser("extract", help="Extract DFS trees and bricks from ChatGPT exports")
    parser_extract.add_argument("input", help="Path to raw conversations.json (Read-Only)")
    parser_extract.add_argument("--output", default="output/nexus", help="Output directory")
    parser_extract.set_defaults(func=cmd_extract)

    # wall
    parser_wall = subparsers.add_parser("wall", help="Build token-aware walls")
    parser_wall.add_argument("--input", default="output/nexus", help="Input directory (bricks/trees)")
    parser_wall.add_argument("--size", type=int, default=32000, help="Target token size (default 32k)")
    parser_wall.set_defaults(func=cmd_wall)

    # sync
    parser_sync = subparsers.add_parser("sync", help="Autonomous ingestion and sync daemon")
    parser_sync.add_argument("--rebuild-index", action="store_true", help="Force clear and rebuild FAISS index")
    parser_sync.set_defaults(func=cmd_sync)

    # ask
    parser_ask = subparsers.add_parser("ask", help="Perform semantic recall and optionally generate answers")
    parser_ask.add_argument("query", help="The query text for semantic recall")
    parser_ask.add_argument("--json", action="store_true", help="Output results in strict JSON format")
    parser_ask.add_argument("--top-k", type=int, default=10, help="Number of top bricks to recall (default 5)")
    parser_ask.set_defaults(func=cmd_ask)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Execute command
    args.func(args)

if __name__ == "__main__":
    main()
