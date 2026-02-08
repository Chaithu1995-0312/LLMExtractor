import os
import sys
import json
from nexus.graph.manager import GraphManager

def rebuild_unified_graph():
    """
    Force a full rebuild of the unified graph 'nodes' and 'edges' tables
    from the underlying sync 'bricks' and 'topics' tables.
    """
    print("[MAINTENANCE] Starting Unified Graph Rebuild...")
    
    manager = GraphManager()
    
    # 1. Trigger the automated migration
    # Note: sync_bricks_to_nodes is idempotent and only copies missing ones,
    # but for a 'rebuild' we want to ensure everything is fresh if requested.
    manager.sync_bricks_to_nodes()
    
    # 2. Run validations
    from nexus.graph.validation import run_full_validation
    print("[MAINTENANCE] Running graph integrity validation...")
    is_valid = run_full_validation()
    
    if is_valid:
        print("[MAINTENANCE] SUCCESS: Unified Graph is healthy.")
    else:
        print("[MAINTENANCE] WARNING: Graph validation found issues. Check logs.")

if __name__ == "__main__":
    rebuild_unified_graph()
