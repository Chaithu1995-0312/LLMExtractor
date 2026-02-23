from nexus.db import get_adapter
import os

def apply_schema():
    if not os.getenv("DATABASE_URL"):
        os.environ["DATABASE_URL"] = "postgresql://nexus:nexus@localhost:5432/nexus"
    
    db = get_adapter()
    schema_path = os.path.join("src", "nexus", "graph", "schema_l3_queue.sql")
    with open(schema_path, "r") as f:
        sql = f.read()
    
    print(f"Applying schema from {schema_path}...")
    db.execute(sql)
    print("Schema applied successfully.")

if __name__ == "__main__":
    apply_schema()
