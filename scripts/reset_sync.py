import sys
import os

# Add src to path to allow imports
sys.path.append(os.path.join(os.getcwd(), 'src'))

from nexus.sync.db import SyncDatabase

def reset_sync_data():
    print("[RESET] Initializing database connection...")
    db = SyncDatabase()
    
    print("[RESET] Truncating sync data (bricks, nodes, edges) and resetting run boundaries...")
    try:
        db.truncate_sync_data()
        print("[RESET] Success. All sync data cleared. Next run will be a full ingestion.")
    except Exception as e:
        print(f"[RESET] Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Simple confirmation check
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        reset_sync_data()
    else:
        confirm = input("This will DELETE ALL BRICKS and reset sync progress. Are you sure? (y/N): ")
        if confirm.lower() == 'y':
            reset_sync_data()
        else:
            print("[RESET] Cancelled.")
