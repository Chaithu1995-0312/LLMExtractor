"""
nexus.memory.memory_service
============================
Top-level orchestrator for all Memory Layer operations.

Exposes four primary flows:
  1. ingest()     — parse ChatGPT export, chunk, embed, persist
  2. retrieve()   — embed query, k-NN search, hydrate, return chunks
  3. summarize()  — retrieve then call llama3:latest with context-only prompt
  4. promote_to_brick() — route a chunk to GraphManager as a canonical Brick

All flows are callable independently.
No flow forces generation on the caller.
The Brick promotion flow routes through GraphManager — never direct SQL.

Ingestion concurrency:
  A threading.Semaphore controls simultaneous Ollama calls so the CPU
  is not overloaded on local machines. Default: 2 concurrent embeddings.

Failure handling:
  - Per-chunk embedding failures are logged and skipped (partial recovery).
  - A failed dataset is marked FAILED but partial chunks are retained.
  - Re-ingestion of the same file creates a new dataset version and skips
    chunk_ids that are already in both MetadataStore and VectorStore.

Invariants:
  - MUST NOT modify GraphManager state except through promote_to_brick().
  - MUST NOT mix memory vectors with graph.nodes FAISS index.
  - Ingestion is idempotent per (conversation_id, message_id, chunk_index).
"""

import json
import logging
import threading
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

from nexus.memory.chunker import Chunker
from nexus.memory.dataset_manager import DatasetManager, MemoryDataset
from nexus.memory.embedder import MemoryEmbedder, OllamaUnavailableError
from nexus.memory.metadata_store import MetadataStore
from nexus.memory.retriever import ChunkResult, MemoryRetriever, RetrievalResult
from nexus.memory.vector_store import ChromaMemoryVectorStore, MemoryVectorStore
from nexus.cognition.confidence_engine import ConfidenceEngine

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OLLAMA_BASE_URL: str = "http://localhost:11434"
SUMMARIZE_MODEL: str = "llama3:latest"
SUMMARIZE_ENDPOINT: str = f"{OLLAMA_BASE_URL}/api/generate"
SUMMARIZE_TIMEOUT: int = 120           # seconds
DEFAULT_INGEST_BATCH_SIZE: int = 32    # chunks per metadata batch-save
DEFAULT_CONCURRENCY_LIMIT: int = 2     # max parallel Ollama embed calls
DEFAULT_RETRIEVE_TOP_K: int = 10
DEFAULT_SUMMARIZE_TOP_K: int = 8


# ---------------------------------------------------------------------------
# MemoryService
# ---------------------------------------------------------------------------

class MemoryService:
    """
    Facade for the entire Memory Layer subsystem.

    Designed to be instantiated once per request handler or worker.
    All heavy objects (ChromaDB client, SQLite connection) are created
    lazily by their respective sub-components.
    """

    def __init__(
        self,
        chunk_size: int = 800,
        overlap: int = 150,
        concurrency_limit: int = DEFAULT_CONCURRENCY_LIMIT,
        vector_store: Optional[MemoryVectorStore] = None,
    ):
        self._chunker = Chunker(chunk_size=chunk_size, overlap=overlap)
        self._embedder = MemoryEmbedder()
        self._vector_store = vector_store or ChromaMemoryVectorStore()
        self._metadata_store = MetadataStore()
        self._dataset_manager = DatasetManager()
        self._retriever = MemoryRetriever(
            embedder=self._embedder,
            vector_store=self._vector_store,
            metadata_store=self._metadata_store,
        )
        self._semaphore = threading.Semaphore(concurrency_limit)

    # =========================================================================
    # 1. INGESTION FLOW
    # =========================================================================

    def ingest(
        self,
        export_data: list,
        source_filename: str = "chatgpt_export.json",
        embedding_model: str = "nomic-embed-text",
        batch_size: int = DEFAULT_INGEST_BATCH_SIZE,
    ) -> Dict[str, Any]:
        """
        Ingest a parsed ChatGPT export JSON into the memory layer.

        Args:
            export_data:     Parsed JSON list (conversations).
            source_filename: Display name for the source file.
            embedding_model: Ollama model used for embedding (informational).
            batch_size:      Chunks to accumulate before a batch SQLite write.

        Returns:
            Ingestion summary dict:
            {
              "dataset_id":   str,
              "status":       "COMPLETE" | "FAILED",
              "total_chunks": int,
              "skipped":      int,
              "errors":       int,
              "conversations":int,
              "elapsed_sec":  float,
            }
        """
        started_at = datetime.now(timezone.utc)

        # 1. Create dataset record.
        dataset: MemoryDataset = self._dataset_manager.create_dataset(
            source_filename=source_filename,
            embedding_model=embedding_model,
        )
        dataset_id = dataset.dataset_id
        logger.info(
            "[MemoryService] Starting ingestion — dataset=%s source='%s'",
            dataset_id, source_filename,
        )

        self._dataset_manager.update_status(dataset_id, status="RUNNING")

        total_chunks = 0
        skipped_chunks = 0
        error_chunks = 0
        conversation_ids_seen = set()
        batch_buffer: list = []

        try:
            # 2. Stream chunks from the Chunker.
            for chunk in self._chunker.chunk_export(export_data, dataset_id=dataset_id):
                conversation_ids_seen.add(chunk.conversation_id)

                # Idempotency: skip if already in both stores.
                if (
                    self._metadata_store.exists(chunk.chunk_id)
                    and self._vector_store.exists(chunk.chunk_id)
                ):
                    skipped_chunks += 1
                    continue

                # 3. Embed with concurrency control.
                vector = self._embed_with_semaphore(chunk.text)
                if vector is None:
                    # Embedding failed after retries — skip this chunk.
                    error_chunks += 1
                    logger.warning(
                        "[MemoryService] Skipping chunk %s due to embedding failure.",
                        chunk.chunk_id,
                    )
                    continue

                # 4. Persist vector to ChromaDB.
                meta = {
                    "dataset_id": dataset_id,
                    "conversation_id": chunk.conversation_id,
                    "message_id": chunk.message_id,
                    "role": chunk.role,
                    "timestamp": chunk.timestamp or "",
                    "source": chunk.source,
                    "chunk_index": chunk.chunk_index,
                }
                self._vector_store.add(
                    chunk_id=chunk.chunk_id,
                    vector=vector,
                    metadata=meta,
                    text=chunk.text,
                )

                # 5. Accumulate into batch for SQLite write.
                batch_buffer.append(chunk)
                if len(batch_buffer) >= batch_size:
                    self._metadata_store.save_chunks_batch(batch_buffer)
                    total_chunks += len(batch_buffer)
                    logger.debug(
                        "[MemoryService] Flushed batch of %d chunks (total=%d).",
                        len(batch_buffer), total_chunks,
                    )
                    batch_buffer = []

            # Flush remaining batch.
            if batch_buffer:
                self._metadata_store.save_chunks_batch(batch_buffer)
                total_chunks += len(batch_buffer)

            # 6. Mark dataset COMPLETE.
            self._dataset_manager.update_status(
                dataset_id,
                status="COMPLETE",
                total_chunks=total_chunks,
                total_conversations=len(conversation_ids_seen),
            )
            final_status = "COMPLETE"

        except Exception as exc:
            logger.error(
                "[MemoryService] Ingestion failed for dataset %s: %s",
                dataset_id, exc, exc_info=True,
            )
            # Flush partial batch on failure — preserve what was indexed.
            if batch_buffer:
                try:
                    self._metadata_store.save_chunks_batch(batch_buffer)
                    total_chunks += len(batch_buffer)
                except Exception as flush_err:
                    logger.error(
                        "[MemoryService] Batch flush on failure also failed: %s", flush_err
                    )

            self._dataset_manager.update_status(
                dataset_id,
                status="FAILED",
                total_chunks=total_chunks,
                total_conversations=len(conversation_ids_seen),
                error_message=str(exc)[:500],
            )
            final_status = "FAILED"

        elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()

        summary = {
            "dataset_id": dataset_id,
            "status": final_status,
            "total_chunks": total_chunks,
            "skipped": skipped_chunks,
            "errors": error_chunks,
            "conversations": len(conversation_ids_seen),
            "elapsed_sec": round(elapsed, 2),
        }

        logger.info("[MemoryService] Ingestion summary: %s", summary)
        return summary

    def ingest_file(
        self,
        file_path: str,
        batch_size: int = DEFAULT_INGEST_BATCH_SIZE,
    ) -> Dict[str, Any]:
        """
        Ingest directly from a file path.
        Streams the file to avoid loading the full JSON into memory
        when ijson is available; otherwise falls back to json.load().
        """
        import os
        source_filename = os.path.basename(file_path)

        try:
            import ijson

            # Streaming path: chunk_file() handles the file internally.
            started_at = datetime.now(timezone.utc)
            dataset = self._dataset_manager.create_dataset(source_filename=source_filename)
            dataset_id = dataset.dataset_id
            self._dataset_manager.update_status(dataset_id, status="RUNNING")

            total_chunks = 0
            skipped = 0
            errors = 0
            conv_ids: set = set()
            batch: list = []

            try:
                for chunk in self._chunker.chunk_file(file_path, dataset_id=dataset_id):
                    conv_ids.add(chunk.conversation_id)
                    if (
                        self._metadata_store.exists(chunk.chunk_id)
                        and self._vector_store.exists(chunk.chunk_id)
                    ):
                        skipped += 1
                        continue

                    vector = self._embed_with_semaphore(chunk.text)
                    if vector is None:
                        errors += 1
                        continue

                    meta = {
                        "dataset_id": dataset_id,
                        "conversation_id": chunk.conversation_id,
                        "message_id": chunk.message_id,
                        "role": chunk.role,
                        "timestamp": chunk.timestamp or "",
                        "source": chunk.source,
                        "chunk_index": chunk.chunk_index,
                    }
                    self._vector_store.add(chunk.chunk_id, vector, meta, chunk.text)
                    batch.append(chunk)

                    if len(batch) >= batch_size:
                        self._metadata_store.save_chunks_batch(batch)
                        total_chunks += len(batch)
                        batch = []

                if batch:
                    self._metadata_store.save_chunks_batch(batch)
                    total_chunks += len(batch)

                self._dataset_manager.update_status(
                    dataset_id, "COMPLETE",
                    total_chunks=total_chunks,
                    total_conversations=len(conv_ids),
                )
                status = "COMPLETE"

            except Exception as exc:
                logger.error("[MemoryService] ingest_file failed: %s", exc, exc_info=True)
                if batch:
                    try:
                        self._metadata_store.save_chunks_batch(batch)
                        total_chunks += len(batch)
                    except Exception:
                        pass
                self._dataset_manager.update_status(
                    dataset_id, "FAILED",
                    total_chunks=total_chunks,
                    total_conversations=len(conv_ids),
                    error_message=str(exc)[:500],
                )
                status = "FAILED"

            elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
            return {
                "dataset_id": dataset_id,
                "status": status,
                "total_chunks": total_chunks,
                "skipped": skipped,
                "errors": errors,
                "conversations": len(conv_ids),
                "elapsed_sec": round(elapsed, 2),
            }

        except ImportError:
            # ijson not available — load full file.
            with open(file_path, "r", encoding="utf-8") as fh:
                export_data = json.load(fh)
            return self.ingest(
                export_data=export_data,
                source_filename=source_filename,
                batch_size=batch_size,
            )

    # =========================================================================
    # 2. RETRIEVAL FLOW
    # =========================================================================

    def retrieve(
        self,
        query: str,
        top_k: int = DEFAULT_RETRIEVE_TOP_K,
        dataset_id: Optional[str] = None,
        role_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Perform semantic retrieval. Returns a serialisable dict.

        Returns:
            {
              "chunks": [
                {"chunk_id": str, "text": str, "score": float, "metadata": dict},
                ...
              ],
              "retrieval_metadata": { ... }
            }
        """
        result: RetrievalResult = self._retriever.retrieve(
            query=query,
            top_k=top_k,
            dataset_id=dataset_id,
            role_filter=role_filter,
        )

        return {
            "chunks": [
                {
                    "chunk_id": c.chunk_id,
                    "text": c.text,
                    "score": c.score,
                    "metadata": c.metadata,
                }
                for c in result.chunks
            ],
            "retrieval_metadata": result.retrieval_metadata,
        }

    # =========================================================================
    # 3. SUMMARIZATION FLOW
    # =========================================================================

    def summarize(
        self,
        query: str,
        top_k: int = DEFAULT_SUMMARIZE_TOP_K,
        dataset_id: Optional[str] = None,
        force_json: bool = False,
    ) -> Dict[str, Any]:
        """
        Retrieve relevant chunks then ask llama3:latest to summarize them.

        System prompt: "Summarize only using provided context."
        No hallucination — model is given only the retrieved texts.

        Args:
            query:      Natural language query.
            top_k:      Chunks to retrieve for context.
            dataset_id: Optional dataset scope.
            force_json: If True, instructs model to return valid JSON.

        Returns:
            {
              "summary":            str,
              "sources":            List[dict],  # chunk_id + score per source
              "retrieval_metadata": dict,
              "model":              str,
              "status":             "success" | "failed" | "no_context",
            }
        """
        # Step 1: Retrieve context chunks.
        retrieval_result: RetrievalResult = self._retriever.retrieve(
            query=query,
            top_k=top_k,
            dataset_id=dataset_id,
        )

        if not retrieval_result.chunks:
            logger.warning("[MemoryService] summarize: no context found for query '%s'.", query[:60])
            return {
                "summary": "",
                "sources": [],
                "retrieval_metadata": retrieval_result.retrieval_metadata,
                "model": SUMMARIZE_MODEL,
                "status": "no_context",
            }

        # Step 1b: Gate on retrieval confidence via ConfidenceEngine.
        # Memory Layer does NOT define its own threshold — delegates to ConfidenceEngine.
        _ce = ConfidenceEngine()
        all_scores = [c.score for c in retrieval_result.chunks]
        retrieved_texts = [c.text for c in retrieval_result.chunks]
        top_score = retrieval_result.retrieval_metadata.get("top_score", 0.0)

        retrieval_conf = _ce.compute_retrieval_confidence(
            top_score=top_score,
            all_scores=all_scores,
            retrieved_texts=retrieved_texts,
            query_text=query,
        )

        if not retrieval_conf["gate_pass"]:
            logger.warning(
                "[MemoryService] summarize: retrieval confidence too low "
                "(%.4f < %.4f) for query '%s'. Blocking generation.",
                retrieval_conf["retrieval_confidence"],
                retrieval_conf["threshold_used"],
                query[:60],
            )
            return {
                "summary": "",
                "sources": [],
                "retrieval_metadata": {
                    **retrieval_result.retrieval_metadata,
                    "retrieval_confidence": retrieval_conf,
                },
                "model": SUMMARIZE_MODEL,
                "status": "insufficient_context",
                "retrieval_confidence": retrieval_conf,
            }

        logger.info(
            "[MemoryService] summarize: retrieval confidence=%.4f (gate_pass=True) for query '%s'.",
            retrieval_conf["retrieval_confidence"],
            query[:60],
        )

        # Step 2: Build context block from top chunks.
        context_parts = []
        for idx, chunk in enumerate(retrieval_result.chunks, start=1):
            context_parts.append(
                f"[{idx}] (score={chunk.score:.3f}, role={chunk.metadata.get('role','?')}):\n{chunk.text}"
            )
        context_block = "\n\n".join(context_parts)

        # Step 3: Build the prompt.
        if force_json:
            instruction = (
                "You are a memory summarizer. Respond ONLY with valid JSON in this format:\n"
                '{"summary": "<summary text>", "key_topics": ["topic1", "topic2"]}\n'
                "Use ONLY the provided context. Do not hallucinate."
            )
        else:
            instruction = (
                "You are a memory summarizer. Summarize the following context "
                "concisely and accurately. Use ONLY the provided context. "
                "Do not hallucinate or add external information."
            )

        full_prompt = (
            f"{instruction}\n\n"
            f"QUERY: {query}\n\n"
            f"CONTEXT:\n{context_block}\n\n"
            f"SUMMARY:"
        )

        # Step 4: Call llama3:latest via Ollama /api/generate.
        try:
            payload = {
                "model": SUMMARIZE_MODEL,
                "prompt": full_prompt,
                "stream": False,
            }
            if force_json:
                payload["format"] = "json"

            response = requests.post(
                SUMMARIZE_ENDPOINT,
                json=payload,
                timeout=SUMMARIZE_TIMEOUT,
            )
            response.raise_for_status()
            body = response.json()
            summary_text = body.get("response", "").strip()

            sources = [
                {"chunk_id": c.chunk_id, "score": c.score, "metadata": c.metadata}
                for c in retrieval_result.chunks
            ]

            return {
                "summary": summary_text,
                "sources": sources,
                "retrieval_metadata": retrieval_result.retrieval_metadata,
                "model": SUMMARIZE_MODEL,
                "status": "success",
            }

        except requests.exceptions.ConnectionError as exc:
            logger.error("[MemoryService] Ollama unavailable for summarization: %s", exc)
            return {
                "summary": "",
                "sources": [],
                "retrieval_metadata": retrieval_result.retrieval_metadata,
                "model": SUMMARIZE_MODEL,
                "status": "failed",
                "error": "ollama_unavailable",
            }
        except Exception as exc:
            logger.error("[MemoryService] summarize() failed: %s", exc, exc_info=True)
            return {
                "summary": "",
                "sources": [],
                "retrieval_metadata": retrieval_result.retrieval_metadata,
                "model": SUMMARIZE_MODEL,
                "status": "failed",
                "error": str(exc)[:300],
            }

    # =========================================================================
    # 4. BRICK PROMOTION FLOW
    # =========================================================================

    def promote_to_brick(
        self,
        chunk_id: str,
        actor: str = "memory_layer",
    ) -> Dict[str, Any]:
        """
        Promote a memory chunk to a canonical Nexus Brick via GraphManager.

        Flow:
          1. Fetch chunk from MetadataStore.
          2. Construct Brick payload (statement, lifecycle, metadata).
          3. Register via GraphManager.register_node() — respects all invariants.
          4. Log the promotion.

        Invariants:
          - DOES NOT bypass GraphManager.
          - DOES NOT write to graph.nodes or sync.bricks directly.
          - The resulting Brick starts at lifecycle='loose'.
          - Full lineage is preserved in node metadata.

        Returns:
            {
              "status":  "success" | "failed" | "not_found",
              "brick_id": str,
              "chunk_id": str,
            }
        """
        # Step 1: Fetch chunk from MetadataStore.
        chunk_row = self._metadata_store.get_chunk(chunk_id)
        if not chunk_row:
            logger.warning(
                "[MemoryService] promote_to_brick: chunk %s not found.", chunk_id
            )
            return {
                "status": "not_found",
                "brick_id": None,
                "chunk_id": chunk_id,
                "error": f"Chunk {chunk_id} not found in MetadataStore.",
            }

        # Step 2: Build the Brick payload.
        import uuid as _uuid
        brick_id = str(_uuid.uuid4())
        statement = chunk_row["text"]

        node_attrs = {
            "statement": statement,
            "lifecycle": "loose",
            "metadata": {
                "promoted_from": "memory_layer",
                "promoted_by": actor,
                "promoted_at": datetime.now(timezone.utc).isoformat(),
                "source_chunk_id": chunk_id,
                "source_conversation_id": chunk_row.get("conversation_id", ""),
                "source_message_id": chunk_row.get("message_id", ""),
                "source_role": chunk_row.get("role", ""),
                "source_timestamp": chunk_row.get("timestamp", ""),
                "source_dataset_id": chunk_row.get("dataset_id", ""),
                "origin": "chatgpt_export",
            },
        }

        # Step 3: Register via GraphManager — all invariants are upheld by GM.
        try:
            from nexus.graph.manager import GraphManager
            gm = GraphManager()
            gm.register_node("brick", brick_id, node_attrs)

            logger.info(
                "[MemoryService] Promoted chunk %s -> brick %s (actor=%s).",
                chunk_id, brick_id, actor,
            )
            return {
                "status": "success",
                "brick_id": brick_id,
                "chunk_id": chunk_id,
                "statement": statement[:200],
            }

        except Exception as exc:
            logger.error(
                "[MemoryService] promote_to_brick failed for chunk %s: %s",
                chunk_id, exc, exc_info=True,
            )
            return {
                "status": "failed",
                "brick_id": None,
                "chunk_id": chunk_id,
                "error": str(exc)[:300],
            }

    # =========================================================================
    # 5. DATASET MANAGEMENT
    # =========================================================================

    def clear_dataset(self, dataset_id: str) -> Dict[str, Any]:
        """
        Clear all vectors and chunks for a dataset. Mark it CLEARED.
        The dataset record is preserved (lineage).
        """
        vec_deleted = self._vector_store.delete_by_dataset(dataset_id)
        meta_deleted = self._metadata_store.delete_by_dataset(dataset_id)
        self._dataset_manager.clear_dataset(dataset_id)

        return {
            "dataset_id": dataset_id,
            "vectors_deleted": vec_deleted,
            "chunks_deleted": meta_deleted,
            "status": "CLEARED",
        }

    def list_datasets(self) -> List[Dict[str, Any]]:
        """Return all dataset records as serialisable dicts."""
        datasets = self._dataset_manager.list_datasets()
        return [asdict(d) for d in datasets]

    def get_dataset(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """Return a single dataset record by ID."""
        ds = self._dataset_manager.get_dataset(dataset_id)
        return asdict(ds) if ds else None

    def index_size(self) -> int:
        """Return the total number of vectors in the memory index."""
        return self._vector_store.count()

    # =========================================================================
    # Internal helpers
    # =========================================================================

    def _embed_with_semaphore(self, text: str) -> Optional[List[float]]:
        """
        Embed text with controlled concurrency (semaphore-gated).
        Returns None on failure after all retries.
        """
        with self._semaphore:
            try:
                return self._embedder.embed(text)
            except OllamaUnavailableError as exc:
                logger.error("[MemoryService] Embedding failed (Ollama unavailable): %s", exc)
                return None
            except Exception as exc:
                logger.error("[MemoryService] Unexpected embedding error: %s", exc)
                return None
