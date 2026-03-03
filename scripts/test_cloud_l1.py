import json
import os
import psycopg2
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

# Cloud DB Config - Use credentials from .env
DB_CONFIG = {
    "dbname": os.getenv("POSTGRES_DB", "nexus"),
    "user": os.getenv("POSTGRES_USER", "nexus"),
    "password": os.getenv("POSTGRES_PASSWORD", "nexus"),
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5432")
}

def simulate_l1_extraction():
    """
    Simulates the Cloud L1 Worker:
    1. Reads one message-batch file.
    2. 'Extracts' concepts (simulated).
    3. Inserts into DB with L1_COMPLETE status.
    """
    batch_dir = "openaiconversations"
    if not os.path.exists(batch_dir):
        print(f"Directory {batch_dir} not found. Run split_conversations.py first.")
        return

    # Find the first message batch file (new format)
    batches = sorted([f for f in os.listdir(batch_dir) if f.startswith("messages_batch_") and f.endswith(".json")])
    if not batches:
        print("No message-batch files found. Run updated split_conversations.py first.")
        return

    target_file = os.path.join(batch_dir, batches[0])
    print(f"🚀 Simulating Cloud L1 on: {target_file}")

    try:
        with open(target_file, "r", encoding="utf-8") as f:
            messages = json.load(f)
    except Exception as e:
        print(f"Error loading {target_file}: {e}")
        return

    print(f"Loaded {len(messages)} messages. Processing...")

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    try:
        inserted_count = 0
        for msg in messages:
            node_id = f"msg_{msg['id']}"
            
            node_data = {
                "statement": msg['content'],
                "lifecycle": "forming",
                "metadata": {
                    "role": msg['role'],
                    "conversation_id": msg['conversation_id'],
                    "model": msg.get("model_slug"),
                    "source_batch": batches[0]
                }
            }

            # Insert into graph.nodes with NEW Status Columns
            cur.execute("""
                INSERT INTO graph.nodes 
                (id, type, data, status, l1_started_at, l1_completed_at, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    status = EXCLUDED.status,
                    l1_completed_at = EXCLUDED.l1_completed_at
            """, (
                node_id,
                'message_node',
                json.dumps(node_data),
                'L1_COMPLETE',
                datetime.now(timezone.utc),
                datetime.now(timezone.utc),
                datetime.now(timezone.utc)
            ))
            inserted_count += 1

        conn.commit()
        print(f"✅ Success! Inserted {inserted_count} nodes with status='L1_COMPLETE'.")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error during simulation: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    simulate_l1_extraction()
