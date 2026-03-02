import os
import psycopg2
from dotenv import load_dotenv

def check_tables():
    load_dotenv()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("Error: DATABASE_URL not set.")
        return

    conn = psycopg2.connect(database_url)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'graph'")
            tables = cur.fetchall()
            print("Tables in 'graph' schema:")
            for t in tables:
                print(f" - {t[0]}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_tables()
