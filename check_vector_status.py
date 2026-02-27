
import os
import sys
import json
from nexus.db import get_adapter

# Add the current directory to sys.path to ensure 'nexus' package is found
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.append(os.path.join(repo_root, "src"))

if __name__ == "__main__":
    db = get_adapter()
    try:
        rows = db.fetch_all("SELECT id, data FROM graph.nodes")
        indexed_count = 0
        pending_count = 0
        other_count = 0

        for row in rows:
            node_id = row[0]
            node_data = row[1] if isinstance(row[1], dict) else json.loads(row[1])
            vector_status = node_data.get("vector_status", "N/A")

            if vector_status == "indexed":
                indexed_count += 1
            elif vector_status == "pending":
                pending_count += 1
            else:
                other_count += 1
        
        print(f"Vector Status Counts:")
        print(f"  Indexed: {indexed_count}")
        print(f"  Pending: {pending_count}")
        print(f"  Other: {other_count}")
        print(f"Total Nodes: {len(rows)}")

    except Exception as e:
        print(f"Error querying vector status: {e}")


