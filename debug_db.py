import sqlite3
import os
import sys

# Adjust path to import nexus modules if necessary
sys.path.append(os.path.join(os.getcwd(), "src"))

# Using the test database path for debugging purposes
# Using the main database path for debugging purposes
DB_PATH = "src/nexus/graph/graph.db"

def get_brick_count_and_path():
    print(f"[DebugDB] Connecting to database at: {DB_PATH}")
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM bricks")
        count = cursor.fetchone()[0]
        print(f"[DebugDB] Found {count} bricks in the 'bricks' table.")
    except Exception as e:
        print(f"[DebugDB] Error accessing bricks table: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    get_brick_count_and_path()
