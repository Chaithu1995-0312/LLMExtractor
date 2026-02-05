import os
import json
import uuid
from pathlib import Path
from typing import List, Dict
import numpy as np

# Importing existing Nexus components
try:
    from nexus.vector.pinecone_index import PineconeVectorIndex
except Exception as e:
    print(f"⚠️ Could not import PineconeVectorIndex: {e}")
    PineconeVectorIndex = None

from nexus.cognition.assembler import assemble_topic
from nexus.vector.embedder import get_embedder
from nexus.config import DATA_DIR

# --- CONFIGURATION ---
INPUT_DIR = os.getenv("NEXUS_INPUT_DIR", "./history_archive")
PC_API_KEY = os.getenv("PINECONE_API_KEY","")

class NexusIngestor:
    def __init__(self, api_key: str, dry_run: bool = False):
        self.dry_run = dry_run
        if not dry_run:
            if not api_key:
                raise ValueError("PINECONE_API_KEY environment variable is required.")
            if PineconeVectorIndex is None:
                print("❌ PineconeVectorIndex is not available. Forcing DRY_RUN.")
                self.dry_run = True
                self.index = None
            else:
                self.index = PineconeVectorIndex(api_key=api_key)
        else:
            print("🏗️ Running in DRY_RUN mode. Pinecone and Neo4j updates will be skipped.")
            self.index = None
        self.embedder = get_embedder()

    def brickify(self, content: str, source_name: str) -> List[Dict]:
        """
        Chunks text into atomic bricks for the vector index.
        Uses a simple paragraph-based splitting to avoid cutting formulas or diagrams.
        """
        # Split by double newlines to preserve structural blocks (paragraphs, formulas, etc.)
        raw_blocks = [b.strip() for b in content.split("\n\n") if b.strip()]
        
        bricks = []
        current_chunk = ""
        max_chunk_size = 1000
        
        for block in raw_blocks:
            if len(current_chunk) + len(block) > max_chunk_size and current_chunk:
                bricks.append({
                    "brick_id": str(uuid.uuid4()),
                    "source_file": str(source_name),
                    "content": current_chunk.strip()
                })
                current_chunk = block
            else:
                current_chunk += "\n\n" + block if current_chunk else block
        
        if current_chunk:
            bricks.append({
                "brick_id": str(uuid.uuid4()),
                "source_file": str(source_name),
                "content": current_chunk.strip()
            })
            
        return bricks

    def ingest_history(self, input_path: str = INPUT_DIR):
        path = Path(input_path)
        if not path.exists():
            print(f"⚠️ Input directory not found: {input_path}")
            return

        for file_path in path.rglob("*"):
            if file_path.suffix not in [".json", ".md"]:
                continue
            
            print(f"📦 Processing: {file_path.name}")
            try:
                content = file_path.read_text(encoding="utf-8")
                
                # STAGE 1: Vector Ingestion
                # Bricks must exist in Pinecone before the Assembler can 'recall' them
                bricks = self.brickify(content, file_path)
                if not bricks:
                    continue
                
                texts = [b["content"] for b in bricks]
                embeddings_np = self.embedder.embed_texts(texts)
                
                # Ensure we have the correct dimensions (Pinecone index is 1536, our local model is 384)
                # If there's a mismatch, we might need to pad or use a different model.
                # In Nexus 2026, we assume the index matches the embedder or we use OpenAI.
                # For this implementation, we convert to list for the upsert_bricks method.
                embeddings = embeddings_np.tolist()
                
                # Check for dimension mismatch (example: local 384 vs expected 1536)
                if len(embeddings[0]) != 1536:
                    print(f"⚠️ Dimension mismatch: Local {len(embeddings[0])} vs Pinecone 1536. Padding with zeros.")
                    padded_embeddings = []
                    for emb in embeddings:
                        padded = emb + [0.0] * (1536 - len(emb))
                        padded_embeddings.append(padded)
                    embeddings = padded_embeddings

                if not self.dry_run:
                    self.index.upsert_bricks(bricks, embeddings)
                else:
                    print(f"🌵 [DRY_RUN] Would upsert {len(bricks)} bricks to Pinecone.")
                
                # STAGE 2: Semantic Assembly & Graph Linkage
                topic_query = file_path.stem.replace("_", " ").title()
                print(f"🧠 Assembling Topic: {topic_query}")
                
                if not self.dry_run:
                    assemble_topic(topic_query)
                else:
                    print(f"🌵 [DRY_RUN] Would trigger assemble_topic('{topic_query}')")
                
            except Exception as e:
                print(f"❌ Error processing {file_path.name}: {e}")

if __name__ == "__main__":
    # Check if we should run in dry run mode if no API key is present
    dry_run = PC_API_KEY is None or PC_API_KEY == ""
    ingestor = NexusIngestor(api_key=PC_API_KEY, dry_run=dry_run)
    ingestor.ingest_history()
    print("✅ Nexus Migration Complete.")
