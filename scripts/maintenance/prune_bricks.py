import os
import json
import sys
from typing import List, Dict

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src")))

from nexus.bricks.brick_store import BrickStore
from nexus.graph.manager import GraphManager

def prune_bricks(dry_run: bool = True):
    print(f"Starting Prune (Dry Run: {dry_run})")
    
    store = BrickStore()
    graph = GraphManager()
    
    bricks_to_delete_by_file = {} # file_path -> [brick_id]
    orphaned_count = 0
    
    # store.metadata_store is loaded on init
    print(f"Loaded metadata for {len(store.metadata_store)} bricks.")
    
    for brick_id, meta in store.metadata_store.items():
        source_file = meta.get("source_file")
        if not source_file:
             pass 
        elif not os.path.exists(source_file):
            # Orphaned!
            orphaned_count += 1
            brick_file_path = meta.get("file_path")
            if brick_file_path:
                if brick_file_path not in bricks_to_delete_by_file:
                    bricks_to_delete_by_file[brick_file_path] = []
                bricks_to_delete_by_file[brick_file_path].append(brick_id)

    print(f"Found {orphaned_count} orphaned bricks.")
    
    if orphaned_count == 0:
        return

    for brick_file_path, brick_ids in bricks_to_delete_by_file.items():
        print(f"Processing {brick_file_path}: removing {len(brick_ids)} bricks")
        
        if not dry_run:
            # 1. Update Brick File
            try:
                if not os.path.exists(brick_file_path):
                     print(f"  Warning: Brick file {brick_file_path} vanished during processing.")
                     continue

                with open(brick_file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                original_len = len(data)
                new_data = [b for b in data if b["brick_id"] not in brick_ids]
                
                if len(new_data) == original_len:
                     print("  Warning: No bricks removed from file (IDs mismatched?).")
                
                if not new_data:
                    os.remove(brick_file_path)
                    print(f"  Deleted empty file: {brick_file_path}")
                else:
                    with open(brick_file_path, "w", encoding="utf-8") as f:
                        json.dump(new_data, f, indent=2)
                    print(f"  Updated file: {brick_file_path} (kept {len(new_data)}/{original_len})")

                # 2. Update Graph
                for bid in brick_ids:
                    if graph.delete_node(bid):
                        print(f"  Deleted graph node: {bid}")
                    else:
                        pass
                        
            except Exception as e:
                print(f"Error processing {brick_file_path}: {e}")

if __name__ == "__main__":
    dry_run = True
    if "--force" in sys.argv or "--act" in sys.argv:
        dry_run = False
    
    if dry_run:
        print("Running in DRY RUN mode. Use --force to execute changes.")
        
    prune_bricks(dry_run=dry_run)
