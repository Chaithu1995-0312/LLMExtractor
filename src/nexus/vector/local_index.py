from pathlib import Path
import json
import numpy as np
import faiss
import os
from typing import List, Dict
from nexus.config import INDEX_PATH, BRICK_IDS_PATH
from nexus.vector.embedder import get_embedder

class LocalVectorIndex:
    def __init__(self):
        self.index_file = Path(INDEX_PATH)
        self.meta_file = Path(BRICK_IDS_PATH)

        self.dimension = 384
        self.index = faiss.IndexFlatL2(self.dimension)
        self.brick_ids: List[str] = []

        if self.index_file.exists() and self.meta_file.exists():
            self.load()
        print("DEBUG FAISS index ntotal =", self.index.ntotal)


    def load(self):
        self.index = faiss.read_index(str(self.index_file))
        with open(self.meta_file, "r", encoding="utf-8") as f:
            self.brick_ids = json.load(f)

    def save(self):
        self.index_file.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(self.index_file))
        with open(self.meta_file, "w", encoding="utf-8") as f:
            json.dump(self.brick_ids, f)

    def add_bricks(self, bricks: List[Dict]):
        pending = [b for b in bricks if b.get("status") == "PENDING"]
        if not pending:
            return

        texts = [b["content"] for b in pending]

        # Real embeddings via Singleton Embedder
        embedder = get_embedder()
        embeddings = embedder.embed_texts(texts)

        self.index.add(embeddings)
        for b in pending:
            self.brick_ids.append(b["brick_id"])
            b["status"] = "EMBEDDED"

    def search(self, query_vector: np.ndarray, k: int = 5):
        if self.index.ntotal == 0:
            return [], []

        distances, indices = self.index.search(query_vector, k)
        return distances[0], indices[0]
