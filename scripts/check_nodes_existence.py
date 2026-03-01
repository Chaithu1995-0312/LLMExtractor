import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def check_nodes_table():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set")
        return

    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM information_schema.tables WHERE table_schema = 'graph' AND table_name = 'nodes'")
        exists = cur.fetchone()
        print(f"EXISTS: {bool(exists)}")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == '__main__':
    check_nodes_table()
