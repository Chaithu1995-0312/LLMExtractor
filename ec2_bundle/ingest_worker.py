import os
import json
import asyncio
import boto3
from datetime import datetime, timezone
from typing import List, Dict, Any

# Mocking parts of the system for a flat EC2 bundle
# In a real setup, we'd include compiler.py as is, but here we'll simplify 
# to ensure it runs without complex local package dependencies.

from llm import StructuredIngestLLM, ExtractionResponse

# --- CONFIG ---
BUCKET = os.getenv("NEXUS_S3_BUCKET", "chat-bricks-bucket")
PREFIX = "nexus/runs/"
INPUT_FILE = "conversations.json"

class EC2IngestWorker:
    def __init__(self):
        self.llm = StructuredIngestLLM()

    async def process_batch(self, messages: List[Dict], topic: Dict) -> List[Dict]:
        prompt = f"""
SCAN SOURCE JSON and extract technical rules/constraints for: {topic['id']}
DEFINITION: {topic['description']}

SOURCE:
{json.dumps(messages)}
"""
        resp: ExtractionResponse = await self.llm.extract(prompt)
        return [p.dict() for p in resp.extracted_pointers]

    async def run(self):
        print(f"[{datetime.now().isoformat()}] Starting ingestion...")
        
        if not os.path.exists(INPUT_FILE):
            print(f"Error: {INPUT_FILE} not found.")
            return

        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            conversations = json.load(f)

        # For this minimal version, we define a default topic to scan for
        topic = {
            "id": "nexus-server-sync",
            "description": "Technical constraints and architectural decisions for Nexus Sync."
        }

        all_pointers = []
        
        # Simple message extraction loop (authoritative roles only)
        for conv in conversations:
            messages = [
                m for m in conv.get("messages", []) 
                if m.get("role") in ("user", "system")
            ]
            
            # Batching (1 message at a time for stability on 2 vCPU)
            for i, msg in enumerate(messages):
                print(f"Processing message {i+1}/{len(messages)} in {conv.get('title', 'Untitled')}")
                batch_pointers = await self.process_batch([msg], topic)
                all_pointers.extend(batch_pointers)

        output = {
            "run_id": f"run_{int(datetime.now().timestamp())}",
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "extracted_pointers": all_pointers
        }

        output_file = "compiled_output.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)

        print(f"Ingestion complete. Found {len(all_pointers)} pointers.")
        self.upload_to_s3(output_file)

    def upload_to_s3(self, file_path: str):
        s3 = boto3.client("s3")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        key = f"{PREFIX}{timestamp}_run.json"
        
        print(f"Uploading to s3://{BUCKET}/{key}...")
        try:
            s3.upload_file(file_path, BUCKET, key)
            print("Upload successful.")
        except Exception as e:
            print(f"Upload failed: {e}")

if __name__ == "__main__":
    worker = EC2IngestWorker()
    asyncio.run(worker.run())
