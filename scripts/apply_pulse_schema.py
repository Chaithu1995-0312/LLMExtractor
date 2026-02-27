"""
Apply the pulse_events schema migration.
Run: python scripts/apply_pulse_schema.py
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv
load_dotenv()

import psycopg2

def main():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL not set")

    schema_path = os.path.join(
        os.path.dirname(__file__), "..", "src", "nexus", "graph", "schema_pulse.sql"
    )
    with open(schema_path, "r", encoding="utf-8") as f:
        sql = f.read()

    conn = psycopg2.connect(database_url)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.close()
    print("[OK] graph.pulse_events table and indexes created (or already existed).")

if __name__ == "__main__":
    main()
