import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# DB Config
DB_CONFIG = {
    "dbname": os.getenv("POSTGRES_DB", "nexus"),
    "user": os.getenv("POSTGRES_USER", "nexus"),
    "password": os.getenv("POSTGRES_PASSWORD", "nexus"),
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5432")
}

def apply_migration():
    sql_file = "src/nexus/graph/schema_status_tracking.sql"
    if not os.path.exists(sql_file):
        print(f"Error: SQL file {sql_file} not found.")
        return

    print(f"Applying migration from {sql_file}...")
    
    try:
        with open(sql_file, "r", encoding="utf-8") as f:
            sql_content = f.read()

        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Execute the SQL block
        cur.execute(sql_content)
        
        conn.commit()
        print("✅ Migration applied successfully.")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
    finally:
        if 'cur' in locals(): cur.close()
        if 'conn' in locals(): conn.close()

if __name__ == "__main__":
    apply_migration()
