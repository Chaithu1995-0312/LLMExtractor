import os
import psycopg2
from dotenv import load_dotenv

def apply_schema():
    load_dotenv()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("Error: DATABASE_URL not set.")
        return

    schema_path = "src/nexus/graph/schema_l3_clustering.sql"
    with open(schema_path, "r") as f:
        sql = f.read()

    print(f"Applying schema from {schema_path}...")
    conn = psycopg2.connect(database_url)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql)
        print("Schema applied successfully.")
    except Exception as e:
        print(f"Error applying schema: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    apply_schema()
