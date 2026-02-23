import os
import sys

# Add src to path to allow imports
sys.path.append(os.path.join(os.getcwd(), 'src'))

from dotenv import load_dotenv

# Load .env to ensure DATABASE_URL is available
load_dotenv()

from nexus.db import get_adapter

def apply_migration():
    print("[MIGRATE] Connecting to database...")
    db = get_adapter()
    
    print("[MIGRATE] Applying schema_cognition.sql...")
    try:
        with open("src/nexus/graph/schema_cognition.sql", "r") as f:
            sql = f.read()
            db.execute(sql)
        print("[MIGRATE] Success: graph.cognition_logs table created.")
    except Exception as e:
        print(f"[MIGRATE] Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    apply_migration()
