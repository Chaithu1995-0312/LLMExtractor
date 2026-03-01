"""
nexus.memory.vector_store
=========================
Vector store abstraction for the Memory Layer.

Interface: MemoryVectorStore (ABC)
Implementation: ChromaMemoryVectorStore

The abstraction exists so ChromaDB can later be swapped for pgvector
without touching any caller code. Callers interact only with the ABC.

ChromaDB collection: "memory_chat_exports"
  - Persisted to disk at data/memory_chroma/ (see _db.get_chroma_persist_dir()).
  - MUST NOT share a collection name with any other Nexus vector store.
  - Supports metadata filtering on dataset_id, role, conversation_id.

Invariants:
  - add() is idempotent: inserting a chunk_id that already exists is a no-op.
  - delete_by_dataset() removes ALL vectors for a dataset atomically.
  - search() returns results ordered by cosine similarity descending.
  - The ChromaDB collection is the ONLY persistent store for memory vectors.
    FAISS (used by GraphManager) is never touched by this module.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from nexus.memory._db import get_chroma_persist_dir

logger = logging.getLogger(__name__)

# Collection name — must be unique across the entire Nexus installation.
MEMORY_COLLECTION_NAME: str = "memory_chat_exports"


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

class MemoryVectorStore(ABC):
    """
    Abstract vector store for the Memory Layer.

    All implementations must be idempotent on add() and support
    metadata-filtered search and dataset-scoped deletion.
    """

    @abstractmethod
    def add(
        self,
        chunk_id: str,
        vector: List[float],
        metadata: Dict[str, Any],
        text: str,
    ) -> None:
        """
        Insert a chunk into the store. Idempotent: skip if chunk_id exists.

        Args:
            chunk_id: Deterministic SHA256 chunk identifier.
            vector:   Embedding vector (float list).
            metadata: Lineage dict (dataset_id, role, conversation_id, …).
            text:     Original chunk text (stored alongside for retrieval).
        """

    @abstractmethod
    def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find the top_k most similar chunks to query_vector.

        Args:
            query_vector: Embedded query (must match stored dimension).
            top_k:        Number of results to return.
            where:        Optional ChromaDB-style metadata filter dict,
                          e.g. {"dataset_id": "abc"} or {"role": "user"}.

        Returns:
            List of result dicts, ordered by similarity descending:
            [
              {
                "chunk_id": str,
                "text":     str,
                "score":    float,   # cosine similarity [0, 1]
                "metadata": dict,
              },
              …
            ]
        """

    @abstractmethod
    def delete_by_dataset(self, dataset_id: str) -> int:
        """
        Delete all vectors associated with a dataset_id.
        Returns the number of vectors deleted.
        """

    @abstractmethod
    def exists(self, chunk_id: str) -> bool:
        """Return True if chunk_id is already indexed."""

    @abstractmethod
    def count(self) -> int:
        """Return total number of vectors in the store."""

    @abstractmethod
    def count_by_dataset(self, dataset_id: str) -> int:
        """Return the number of vectors for a specific dataset."""


# ---------------------------------------------------------------------------
# ChromaDB implementation
# ---------------------------------------------------------------------------

class ChromaMemoryVectorStore(MemoryVectorStore):
    """
    ChromaDB-backed implementation of MemoryVectorStore.

    Persistence: data/memory_chroma/  (local disk, survives restarts)
    Distance:    cosine similarity (chromadb default for embedding functions
                 is L2, so we specify cosine explicitly via metadata config).

    ChromaDB version assumption: chromadb >= 0.4.x
    """

    def __init__(
        self,
        collection_name: str = MEMORY_COLLECTION_NAME,
        persist_dir: Optional[str] = None,
    ):
        self._collection_name = collection_name
        self._persist_dir = persist_dir or get_chroma_persist_dir()
        self._client = None
        self._collection = None
        self._init_client()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init_client(self) -> None:
        """
        Lazily initialise the ChromaDB persistent client.
        Raises ImportError with a clear message if chromadb is not installed.
        """
        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError as exc:
            raise ImportError(
                "chromadb is required for the Memory Layer. "
                "Install it with: pip install chromadb"
            ) from exc

        self._client = chromadb.PersistentClient(path=self._persist_dir)

        # Get-or-create the collection with cosine distance.
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        logger.info(
            "[ChromaMemoryVectorStore] Collection '%s' ready at %s (count=%d).",
            self._collection_name,
            self._persist_dir,
            self._collection.count(),
        )

    def _ensure_ready(self) -> None:
        """Guard: raise if collection is not initialised (should never happen)."""
        if self._collection is None:
            raise RuntimeError(
                "[ChromaMemoryVectorStore] Collection not initialised. "
                "Call _init_client() first."
            )

    # ------------------------------------------------------------------
    # MemoryVectorStore interface
    # ------------------------------------------------------------------

    def add(
        self,
        chunk_id: str,
        vector: List[float],
        metadata: Dict[str, Any],
        text: str,
    ) -> None:
        """
        Idempotent upsert. ChromaDB upsert semantics:
          - If chunk_id exists → overwrite (treated as no-op for identical data).
          - If not → insert.

        We use upsert (not add) to guarantee idempotency on re-ingestion.
        """
        self._ensure_ready()

        # Sanitise metadata: ChromaDB only accepts str/int/float/bool values.
        safe_meta = _sanitise_metadata(metadata)

        try:
            self._collection.upsert(
                ids=[chunk_id],
                embeddings=[vector],
                documents=[text],
                metadatas=[safe_meta],
            )
        except Exception as exc:
            logger.error(
                "[ChromaMemoryVectorStore] Failed to upsert chunk %s: %s",
                chunk_id, exc,
            )
            raise

    def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        k-NN cosine search against the collection.

        ChromaDB returns distances in [0, 2] for cosine space (0 = identical,
        2 = opposite). We convert to similarity score in [0, 1] via:
            score = 1 - (distance / 2)
        """
        self._ensure_ready()

        total = self._collection.count()
        if total == 0:
            return []

        # Clamp top_k to actual collection size.
        effective_k = min(top_k, total)

        query_kwargs: Dict[str, Any] = {
            "query_embeddings": [query_vector],
            "n_results": effective_k,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            query_kwargs["where"] = where

        try:
            results = self._collection.query(**query_kwargs)
        except Exception as exc:
            logger.error("[ChromaMemoryVectorStore] search() failed: %s", exc)
            raise

        # Unpack ChromaDB response.
        ids = results.get("ids", [[]])[0]
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        output = []
        for cid, doc, meta, dist in zip(ids, docs, metas, distances):
            # Convert cosine distance [0,2] -> similarity [0,1].
            score = max(0.0, min(1.0, 1.0 - (float(dist) / 2.0)))
            output.append(
                {
                    "chunk_id": cid,
                    "text": doc,
                    "score": round(score, 6),
                    "metadata": meta or {},
                }
            )

        return output

    def delete_by_dataset(self, dataset_id: str) -> int:
        """
        Delete all vectors tagged with dataset_id.
        Uses ChromaDB's where-filter delete.
        """
        self._ensure_ready()

        try:
            # First count how many will be deleted.
            existing = self._collection.get(
                where={"dataset_id": dataset_id},
                include=[],
            )
            ids_to_delete = existing.get("ids", [])
            count = len(ids_to_delete)

            if count > 0:
                self._collection.delete(where={"dataset_id": dataset_id})
                logger.info(
                    "[ChromaMemoryVectorStore] Deleted %d vectors for dataset %s.",
                    count, dataset_id,
                )
            return count
        except Exception as exc:
            logger.error(
                "[ChromaMemoryVectorStore] delete_by_dataset(%s) failed: %s",
                dataset_id, exc,
            )
            raise

    def exists(self, chunk_id: str) -> bool:
        """Return True if the chunk_id is already in the collection."""
        self._ensure_ready()
        try:
            result = self._collection.get(ids=[chunk_id], include=[])
            return len(result.get("ids", [])) > 0
        except Exception:
            return False

    def count(self) -> int:
        """Total vector count in the collection."""
        self._ensure_ready()
        return self._collection.count()

    def count_by_dataset(self, dataset_id: str) -> int:
        """Count vectors for a specific dataset."""
        self._ensure_ready()
        try:
            result = self._collection.get(
                where={"dataset_id": dataset_id},
                include=[],
            )
            return len(result.get("ids", []))
        except Exception as exc:
            logger.warning(
                "[ChromaMemoryVectorStore] count_by_dataset(%s) error: %s",
                dataset_id, exc,
            )
            return 0


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _sanitise_metadata(meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    ChromaDB metadata values must be str, int, float, or bool.
    Convert None -> "" and any other types to str.
    """
    safe: Dict[str, Any] = {}
    for k, v in meta.items():
        if v is None:
            safe[k] = ""
        elif isinstance(v, (str, int, float, bool)):
            safe[k] = v
        else:
            safe[k] = str(v)
    return safe
