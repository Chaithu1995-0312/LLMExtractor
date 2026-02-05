import os
import json
from typing import List, Dict, Optional
from pinecone import Pinecone, ServerlessSpec

class PineconeVectorIndex:
    def __init__(self, api_key: str, index_name: str = "nexus-bricks"):
        self.pc = Pinecone(api_key=api_key)
        self.index_name = index_name
        
        # Ensure index exists (Serverless for 2026 standards)
        if index_name not in self.pc.list_indexes().names():
            self.pc.create_index(
                name=index_name,
                dimension=1536, # Default for many embeddings
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
        self.index = self.pc.Index(index_name)

    def upsert_bricks(self, bricks: List[Dict], embeddings: List[List[float]], batch_size: int = 100):
        """
        Upsert bricks in chunks to Pinecone to avoid payload limits.
        Utilizes a generator-friendly approach for massive history migrations.
        """
        def _get_batches(items, size):
            for i in range(0, len(items), size):
                yield items[i:i + size]

        vectors = []
        for brick, emb in zip(bricks, embeddings):
            # 2026 Best Practice: Include more rich metadata for filtering
            vectors.append({
                "id": brick["brick_id"],
                "values": emb,
                "metadata": {
                    "source_file": brick["source_file"],
                    "content": brick["content"][:2000], # Increased context
                    "created_at": brick.get("created_at", ""),
                    "brick_type": brick.get("type", "conversation_fragment")
                }
            })
            
        total_upserted = 0
        for batch in _get_batches(vectors, batch_size):
            try:
                self.index.upsert(vectors=batch)
                total_upserted += len(batch)
                print(f"DEBUG: Upserted {total_upserted}/{len(vectors)} bricks to Pinecone.")
            except Exception as e:
                print(f"ERROR: Pinecone batch upsert failed: {e}")
                # In a real migration, we might want to retry here
                raise e

    def query(self, vector: List[float], k: int = 5):
        return self.index.query(vector=vector, top_k=k, include_metadata=True)
