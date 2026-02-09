import sqlite3
import os

DB_PATH = "test_nexus_p1.db"
SCHEMA_PATH = "src/nexus/graph/schema_sync.sql"

def update_db():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found.")
        return

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.executescript(schema_sql)
        conn.commit()
        conn.close()
        print("Database schema updated successfully.")
    except Exception as e:
        print(f"Error updating database: {e}")

if __name__ == "__main__":
    update_db()
