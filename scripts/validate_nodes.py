import os
import json
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def run_query(query):
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL not set")
        return
    
    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute(query)
        if cur.description:
            rows = cur.fetchall()
            for row in rows:
                print(row)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        run_query(sys.argv[1])
    else:
        # Default check for "Everything Is a Node"
        print("--- Node Types Count ---")
        run_query("SELECT type, COUNT(*) FROM graph.nodes GROUP BY type;")
        print("\n--- Edge Types Count ---")
        run_query("SELECT edge_type, COUNT(*) FROM graph.edges GROUP BY edge_type;")
        print("\n--- Tables check ---")
        run_query("SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema IN ('graph', 'sync', 'governance') ORDER BY table_schema, table_name;")
