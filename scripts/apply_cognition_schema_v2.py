import os
import sys

# Add src to path to allow imports
sys.path.append(os.path.join(os.getcwd(), 'src'))

from dotenv import load_dotenv
load_dotenv()

from nexus.db import get_adapter

def apply_migration_v2():
    print("[MIGRATE] Connecting to database...")
    db = get_adapter()
    
    print("[MIGRATE] Applying schema_cognition_v2.sql...")
    try:
        with open("src/nexus/graph/schema_cognition_v2.sql", "r") as f:
            sql = f.read()
            db.execute(sql)
        print("[MIGRATE] Success: v2_cognition_upgrade applied.")
    except Exception as e:
        print(f"[MIGRATE] Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    apply_migration_v2()
