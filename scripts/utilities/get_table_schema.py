import os
import sys
import psycopg2
from dotenv import load_dotenv

def get_table_schema(table_name: str):
    load_dotenv()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("Error: DATABASE_URL environment variable not set.")
        sys.exit(1)

    try:
        conn = psycopg2.connect(database_url)
        with conn.cursor() as cur:
            # Extract schema and table name from input (e.g., 'sync.bricks' -> schema='sync', table='bricks')
            if '.' in table_name:
                schema_name, simple_table_name = table_name.split('.', 1)
            else:
                # Default to 'public' schema if not specified, or infer from common schemas like 'graph', 'sync'
                # For this task, we assume 'graph' or 'sync' based on prior analysis
                # A more robust solution might query information_schema.tables first
                if table_name == 'nodes':
                    schema_name = 'graph'
                    simple_table_name = 'nodes'
                elif table_name == 'bricks':
                    schema_name = 'sync'
                    simple_table_name = 'bricks'
                else:
                    print(f"Error: Could not infer schema for table '{table_name}'. Please specify as 'schema.table'.")
                    sys.exit(1)

            query = """
                SELECT column_name, data_type, column_default, is_nullable
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position;
            """
            cur.execute(query, (schema_name, simple_table_name))
            columns = cur.fetchall()

            if not columns:
                print(f"No columns found for table '{table_name}' in schema '{schema_name}'. Check table name and schema.")
                sys.exit(0)

            print(f"Schema for table {table_name}:")
            print("--------------------------------------------------------------------------------")
            print(f"{'Column':<30} {'Type':<20} {'Default':<20} {'Nullable':<10}")
            print("--------------------------------------------------------------------------------")
            for col in columns:
                col_name, data_type, col_default, is_nullable = col
                nullable_str = "YES" if is_nullable == "YES" else "NO"
                print(f"{col_name:<30} {data_type:<20} {str(col_default):<20} {nullable_str:<10}")
            print("--------------------------------------------------------------------------------")

    except psycopg2.Error as e:
        print(f"Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python get_table_schema.py <table_name> (e.g., 'sync.bricks')")
        sys.exit(1)
    
    table_arg = sys.argv[1]
    get_table_schema(table_arg)
