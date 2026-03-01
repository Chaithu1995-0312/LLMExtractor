import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

SCHEMA_FILE = "src/nexus/graph/schema_evolution.sql"

def apply_schema():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set")
        return

    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        full_sql = f.read()
    
    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        print(f"Applying full schema from {SCHEMA_FILE}...")
        cur.execute(full_sql)
        conn.commit()
        cur.close()
        conn.close()
        print("Schema application complete.")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == '__main__':
    apply_schema()
