import sqlite3
import os
import json
import glob
from nexus.config import GRAPH_DB_PATH
from nexus.db import get_adapter
from nexus.db.init_db import init_database
from dotenv import load_dotenv

load_dotenv()

def migrate():
    print("🚀 Starting Migration: SQLite + Files -> PostgreSQL")
    
    # 1. Initialize Postgres Schema
    print("Initializing PostgreSQL schema...")
    init_database()
    pg_db = get_adapter()

    # 2. Connect to SQLite
    if not os.path.exists(GRAPH_DB_PATH):
        print(f"⚠️ SQLite DB not found at {GRAPH_DB_PATH}. Skipping SQLite migration.")
        sqlite_conn = None
    else:
        print(f"Connected to SQLite at {GRAPH_DB_PATH}")
        sqlite_conn = sqlite3.connect(GRAPH_DB_PATH)
        sqlite_conn.row_factory = sqlite3.Row

    if sqlite_conn:
        cursor = sqlite_conn.cursor()
        
        # --- MIGRATE TOPICS ---
        try:
            cursor.execute("SELECT * FROM topics")
            rows = cursor.fetchall()
            print(f"Migrating {len(rows)} topics...")
            with pg_db.transaction() as pg_cur:
                for row in rows:
                    pg_cur.execute(
                        """
                        INSERT INTO sync.topics (id, display_name, definition_json, ordering_rule, state)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO NOTHING
                        """,
                        (row['id'], row['display_name'], row['definition_json'], row['ordering_rule'], row['state'])
                    )
        except sqlite3.OperationalError:
            print("Table 'topics' not found in SQLite.")

        # --- MIGRATE SOURCE RUNS ---
        try:
            cursor.execute("SELECT * FROM source_runs")
            rows = cursor.fetchall()
            print(f"Migrating {len(rows)} source_runs...")
            with pg_db.transaction() as pg_cur:
                for row in rows:
                    pg_cur.execute(
                        """
                        INSERT INTO sync.source_runs (id, raw_content, status, last_processed_index)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (id) DO NOTHING
                        """,
                        (row['id'], row['raw_content'], row['status'], row['last_processed_index'])
                    )
        except sqlite3.OperationalError:
            print("Table 'source_runs' not found in SQLite.")

        # --- MIGRATE BRICKS ---
        try:
            cursor.execute("SELECT * FROM bricks")
            rows = cursor.fetchall()
            print(f"Migrating {len(rows)} bricks...")
            with pg_db.transaction() as pg_cur:
                for row in rows:
                    pg_cur.execute(
                        """
                        INSERT INTO sync.bricks (
                            id, topic_id, content, fingerprint, state, 
                            run_id, json_path, start_index, end_index, source_checksum, created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO NOTHING
                        """,
                        (
                            row['id'], row['topic_id'], row['content'], row['fingerprint'], row['state'],
                            row['run_id'], row['json_path'], row['start_index'], row['end_index'], 
                            row['source_checksum'], row['created_at']
                        )
                    )
        except sqlite3.OperationalError:
            print("Table 'bricks' not found in SQLite.")

        # --- MIGRATE NODES ---
        try:
            cursor.execute("SELECT * FROM nodes")
            rows = cursor.fetchall()
            print(f"Migrating {len(rows)} nodes...")
            with pg_db.transaction() as pg_cur:
                for row in rows:
                    pg_cur.execute(
                        """
                        INSERT INTO graph.nodes (id, type, data, created_at)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (id) DO NOTHING
                        """,
                        (row['id'], row['type'], row['data'], row['created_at'])
                    )
        except sqlite3.OperationalError:
            print("Table 'nodes' not found in SQLite.")

        # --- MIGRATE EDGES ---
        try:
            cursor.execute("SELECT * FROM edges")
            rows = cursor.fetchall()
            print(f"Migrating {len(rows)} edges...")
            with pg_db.transaction() as pg_cur:
                for row in rows:
                    pg_cur.execute(
                        """
                        INSERT INTO graph.edges (source_id, target_id, edge_type, metadata, created_at)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                        """,
                        (row['source'], row['target'], row['type'], row['data'], row['created_at'])
                    )
        except sqlite3.OperationalError:
            print("Table 'edges' not found in SQLite.")

        # --- MIGRATE PROMPTS ---
        try:
            cursor.execute("SELECT * FROM prompts")
            rows = cursor.fetchall()
            print(f"Migrating {len(rows)} prompts...")
            with pg_db.transaction() as pg_cur:
                for row in rows:
                    pg_cur.execute(
                        """
                        INSERT INTO governance.prompts (slug, version, content, role, description, metadata, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (slug, version) DO NOTHING
                        """,
                        (row['slug'], row['version'], row['content'], row['role'], row['description'], row['metadata'], row['created_at'])
                    )
        except sqlite3.OperationalError:
            print("Table 'prompts' not found in SQLite.")

        # --- MIGRATE COVERAGE ALERTS ---
        try:
            cursor.execute("SELECT * FROM coverage_alerts")
            rows = cursor.fetchall()
            print(f"Migrating {len(rows)} coverage_alerts...")
            with pg_db.transaction() as pg_cur:
                for row in rows:
                    pg_cur.execute(
                        """
                        INSERT INTO governance.coverage_alerts (
                            alert_id, fingerprint, topic_id, type, severity, signal_score, 
                            state, summary, created_at, updated_at, acknowledged_by, 
                            resolved_by, resolution_action, resolution_metadata, dismissed_reason
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (fingerprint) DO NOTHING
                        """,
                        (
                            row['alert_id'], row['fingerprint'], row['topic_id'], row['type'], row['severity'], row['signal_score'],
                            row['state'], row['summary'], row['created_at'], row['updated_at'], row['acknowledged_by'],
                            row['resolved_by'], row['resolution_action'], row['resolution_metadata'], row['dismissed_reason']
                        )
                    )
        except sqlite3.OperationalError:
            print("Table 'coverage_alerts' not found in SQLite.")

        sqlite_conn.close()

    # --- MIGRATE COGNITIVE SHARDS (FROM FILES) ---
    shard_files = glob.glob("cognitive_shards/*.jsonl")
    print(f"Found {len(shard_files)} cognitive shard files.")
    
    if shard_files:
        with pg_db.transaction() as pg_cur:
            count = 0
            for shard_file in shard_files:
                try:
                    with open(shard_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        # data format: {"shard_id": 0, "text": "..."}
                        shard_id = data.get("shard_id")
                        text = data.get("text")
                        
                        if shard_id is not None and text:
                            pg_cur.execute(
                                """
                                INSERT INTO sync.cognitive_shards (shard_id, text, created_at)
                                VALUES (%s, %s, NOW())
                                """,
                                (shard_id, text)
                            )
                            count += 1
                except Exception as e:
                    print(f"Error reading shard {shard_file}: {e}")
            print(f"Migrated {count} shards to DB.")

    # --- VERIFICATION ---
    print("\n--- VERIFICATION ---")
    
    if sqlite_conn:
        sqlite_conn = sqlite3.connect(GRAPH_DB_PATH) # Reconnect for check
        cursor = sqlite_conn.cursor()
        
        # Check Nodes
        try:
            cursor.execute("SELECT COUNT(*) FROM nodes")
            sq_nodes = cursor.fetchone()[0]
            pg_nodes_res = pg_db.fetch_one("SELECT COUNT(*) FROM graph.nodes")
            pg_nodes = pg_nodes_res[0]
            print(f"Nodes: SQLite={sq_nodes}, Postgres={pg_nodes} -> {'✅ MATCH' if sq_nodes == pg_nodes else '❌ MISMATCH'}")
        except: pass

        # Check Edges
        try:
            cursor.execute("SELECT COUNT(*) FROM edges")
            sq_edges = cursor.fetchone()[0]
            pg_edges_res = pg_db.fetch_one("SELECT COUNT(*) FROM graph.edges")
            pg_edges = pg_edges_res[0]
            print(f"Edges: SQLite={sq_edges}, Postgres={pg_edges} -> {'✅ MATCH' if sq_edges == pg_edges else '❌ MISMATCH'}")
        except: pass
        
        sqlite_conn.close()

    pg_shards_res = pg_db.fetch_one("SELECT COUNT(*) FROM sync.cognitive_shards")
    print(f"Cognitive Shards in Postgres: {pg_shards_res[0]}")

    print("\nMigration Complete.")

if __name__ == "__main__":
    migrate()
