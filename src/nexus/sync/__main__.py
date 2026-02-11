import argparse
import sys
import os

print(f"[DEBUG] sys.path: {sys.path}", flush=True)
print(f"[DEBUG] Current working directory: {os.getcwd()}", flush=True)
sys.dont_write_bytecode = True # Prevent .pyc files

from nexus.sync.runner import run_sync

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nexus Sync")
    parser.add_argument("--rebuild-index", action="store_true", help="Rebuild index from scratch")
    parser.add_argument("--mock", action="store_true", help="Use mock responses for structured LLM calls")
    args = parser.parse_args()

    if args.mock:
        os.environ["LLM_MOCK_INGEST"] = "true"
    
    run_sync("conversations.json", "output/nexus", rebuild_index=args.rebuild_index)
