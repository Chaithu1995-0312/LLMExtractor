import os
from psycopg2 import connect
from dotenv import load_dotenv

load_dotenv()


def init_database():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL not set")

    conn = connect(database_url)
    conn.autocommit = True

    schema_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "graph",
        "schema_postgres.sql"
    )

    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    with conn.cursor() as cur:
        cur.execute(schema_sql)

    conn.close()
    print("PostgreSQL schema initialized successfully.")

if __name__ == "__main__":
    init_database()
