import argparse
from nexus.sync.runner import run_sync

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nexus Sync")
    parser.add_argument("--rebuild-index", action="store_true", help="Rebuild index from scratch")
    args = parser.parse_args()
    
    run_sync("conversations.json", "output/nexus", rebuild_index=args.rebuild_index)
