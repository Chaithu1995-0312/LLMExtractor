import sqlite3
import os

DB_PATH = "src/nexus/graph/graph.db"

def test_db_operations():
    print(f"[TestDB] Connecting to database at: {DB_PATH}")
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 1. Check initial count
        cursor.execute("SELECT COUNT(*) FROM bricks")
        initial_count = cursor.fetchone()[0]
        print(f"[TestDB] Initial brick count: {initial_count}")

        # 2. Delete all bricks
        print("[TestDB] Deleting all bricks...")
        cursor.execute("DELETE FROM bricks")
        conn.commit()

        # 3. Check count after delete
        cursor.execute("SELECT COUNT(*) FROM bricks")
        count_after_delete = cursor.fetchone()[0]
        print(f"[TestDB] Brick count after delete: {count_after_delete}")

        # 4. Insert a test brick
        print("[TestDB] Inserting a test brick...")
        test_brick = {
            "id": "test_brick_1",
            "topic_id": "test_topic",
            "content": "This is a test brick content.",
            "fingerprint": "test_fingerprint",
            "state": "FINAL",
            "run_id": "test_run",
            "json_path": "$.test",
            "start_index": 0,
            "end_index": 10,
            "source_checksum": "test_checksum"
        }
        cursor.execute("""
            INSERT INTO bricks (id, topic_id, content, fingerprint, state, run_id, json_path, start_index, end_index, source_checksum)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            test_brick["id"],
            test_brick["topic_id"],
            test_brick["content"],
            test_brick["fingerprint"],
            test_brick["state"],
            test_brick["run_id"],
            test_brick["json_path"],
            test_brick["start_index"],
            test_brick["end_index"],
            test_brick["source_checksum"]
        ))
        conn.commit()

        # 5. Check count after insert
        cursor.execute("SELECT COUNT(*) FROM bricks")
        count_after_insert = cursor.fetchone()[0]
        print(f"[TestDB] Brick count after insert: {count_after_insert}")

    except Exception as e:
        print(f"[TestDB] Error during DB operations: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    test_db_operations()
