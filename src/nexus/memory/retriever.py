"""
nexus.memory.retriever
======================
Retrieval interface for the Memory Layer.

Orchestrates:
  1. Embed query text via MemoryEmbedder (Ollama nomic-embed-text)
  2. k-NN search via MemoryVectorStore (ChromaDB)
  3. Hydrate results with full chunk text + lineage from MetadataStore

Returns structured RetrievalResult objects — no LLM generation occurs here.

Invariants:
  - MUST NOT call any LLM. Generation is the caller's responsibility.
  - MUST NOT touch GraphManager or any FAISS index.
  - Returns raw chunks with scores. Consumer decides what to do with them.
  - Empty results are valid (returns empty list, not an error).
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from nexus.memory.embedder import MemoryEmbedder
from nexus.memory.metadata_store import MetadataStore
from nexus.memory.vector_store import ChromaMemoryVectorStore, MemoryVectorStore

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class ChunkResult:
    """A single retrieved chunk with its score and lineage metadata."""

    chunk_id: str
    text: str
    score: float
    metadata: Dict[str, Any]


@dataclass
class RetrievalResult:
    """
    Full retrieval response for a single query.

    Returned by MemoryRetriever.retrieve(). Contains the ranked chunks
    plus diagnostic metadata about the retrieval operation.
    """

    chunks: List[ChunkResult]
    retrieval_metadata: Dict[str, Any]


# ---------------------------------------------------------------------------
# Retriever
# ---------------------------------------------------------------------------

class MemoryRetriever:
    """
    Semantic retriever for the Memory Layer.

    Usage:
        retriever = MemoryRetriever()
        result = retriever.retrieve("What did we discuss about async patterns?", top_k=5)

        for chunk in result.chunks:
            print(chunk.score, chunk.text[:200])

    The retriever is stateless beyond its component references and is safe
    to share across threads (embedder and vector store are each thread-safe
    for read operations).
    """

    def __init__(
        self,
        embedder: Optional[MemoryEmbedder] = None,
        vector_store: Optional[MemoryVectorStore] = None,
        metadata_store: Optional[MetadataStore] = None,
    ):
        self._embedder = embedder or MemoryEmbedder()
        self._vector_store = vector_store or ChromaMemoryVectorStore()
        self._metadata_store = metadata_store or MetadataStore()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        dataset_id: Optional[str] = None,
        role_filter: Optional[str] = None,
    ) -> RetrievalResult:
        """
        Perform semantic retrieval for a natural language query.

        Args:
            query:       Natural language question or topic.
            top_k:       Maximum number of chunks to return.
            dataset_id:  If provided, restrict search to this dataset only.
            role_filter: If provided, restrict to 'user' or 'assistant' chunks.

        Returns:
            RetrievalResult with ranked chunks and retrieval diagnostics.
        """
        started_at = datetime.now(timezone.utc)

        if not query or not query.strip():
            logger.warning("[MemoryRetriever] Empty query — returning empty result.")
            return RetrievalResult(
                chunks=[],
                retrieval_metadata={
                    "model_used": self._embedder.model,
                    "index_size": self._vector_store.count(),
                    "mean_score": 0.0,
                    "top_score": 0.0,
                    "timestamp": started_at.isoformat(),
                    "query_tokens": 0,
                    "error": "empty_query",
                },
            )

        # Step 1: Embed the query.
        query_vector = self._embedder.embed(query)

        # Step 2: Build optional metadata filter for ChromaDB.
        where_filter: Optional[Dict[str, Any]] = None
        filter_clauses: List[Dict[str, Any]] = []

        if dataset_id:
            filter_clauses.append({"dataset_id": dataset_id})
        if role_filter:
            filter_clauses.append({"role": role_filter})

        if len(filter_clauses) == 1:
            where_filter = filter_clauses[0]
        elif len(filter_clauses) > 1:
            # ChromaDB $and operator for multiple filters.
            where_filter = {"$and": filter_clauses}

        # Step 3: k-NN search.
        raw_results = self._vector_store.search(
            query_vector=query_vector,
            top_k=top_k,
            where=where_filter,
        )

        # Step 4: Hydrate with metadata from SQLite.
        chunk_ids = [r["chunk_id"] for r in raw_results]
        stored_meta = self._metadata_store.get_chunks_by_ids(chunk_ids)

        # Step 5: Build ChunkResult list.
        chunk_results: List[ChunkResult] = []
        for raw in raw_results:
            cid = raw["chunk_id"]
            db_row = stored_meta.get(cid, {})

            # Merge: Chroma text is canonical for content.
            # SQLite row provides the full lineage metadata.
            merged_metadata = {
                "conversation_id": db_row.get("conversation_id", raw["metadata"].get("conversation_id", "")),
                "message_id": db_row.get("message_id", raw["metadata"].get("message_id", "")),
                "role": db_row.get("role", raw["metadata"].get("role", "")),
                "timestamp": db_row.get("timestamp", raw["metadata"].get("timestamp", "")),
                "source": db_row.get("source", raw["metadata"].get("source", "chatgpt_export")),
                "dataset_id": db_row.get("dataset_id", raw["metadata"].get("dataset_id", "")),
                "chunk_index": db_row.get("chunk_index", raw["metadata"].get("chunk_index", 0)),
                "token_count": db_row.get("token_count", 0),
            }

            chunk_results.append(
                ChunkResult(
                    chunk_id=cid,
                    text=raw["text"],
                    score=raw["score"],
                    metadata=merged_metadata,
                )
            )

        # Step 6: Compute diagnostic metadata.
        scores = [c.score for c in chunk_results]
        mean_score = (sum(scores) / len(scores)) if scores else 0.0
        top_score = max(scores) if scores else 0.0
        elapsed_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)

        retrieval_metadata = {
            "model_used": self._embedder.model,
            "index_size": self._vector_store.count(),
            "mean_score": round(mean_score, 6),
            "top_score": round(top_score, 6),
            "timestamp": started_at.isoformat(),
            "elapsed_ms": elapsed_ms,
            "returned_chunks": len(chunk_results),
            "top_k_requested": top_k,
            "dataset_filter": dataset_id,
            "role_filter": role_filter,
        }

        logger.info(
            "[MemoryRetriever] query='%s...' top_k=%d returned=%d top_score=%.4f elapsed=%dms",
            query[:60], top_k, len(chunk_results), top_score, elapsed_ms,
        )

        return RetrievalResult(chunks=chunk_results, retrieval_metadata=retrieval_metadata)

    def retrieve_raw_texts(
        self,
        query: str,
        top_k: int = 5,
        dataset_id: Optional[str] = None,
    ) -> List[str]:
        """
        Convenience helper: return only the text strings of top_k matches.
        Used by the summarization flow to build context windows.
        """
        result = self.retrieve(query=query, top_k=top_k, dataset_id=dataset_id)
        return [c.text for c in result.chunks]
