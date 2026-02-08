import sqlite3
import json
import os

db_path = "src/nexus/graph/graph.db"
if not os.path.exists(db_path):
    print(f"DB not found at {db_path}")
else:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT id, type, data FROM nodes")
    rows = c.fetchall()
    print(f"Total nodes: {len(rows)}")
    for r in rows:
        print(f"ID: {r[0]}, Type: {r[1]}, Data: {r[2]}")
    conn.close()
