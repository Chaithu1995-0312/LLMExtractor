"""
nexus.memory.metadata_store
============================
SQLite-backed store for chunk text and metadata lineage.

Responsibility:
  Persist the full text and all lineage fields for every indexed chunk so
  that retrieval hydration (turning a chunk_id back into text + metadata)
  never requires round-tripping to ChromaDB.

This is the single source of truth for:
  - chunk text
  - conversation_id, message_id, role, timestamp
  - dataset_id (for dataset-scoped operations)
  - token_count

The ChromaDB store holds the vectors and allows similarity search.
MetadataStore holds the content and allows hydration by chunk_id.
Both are required for full retrieval. Neither replaces the other.

Invariants:
  - save_chunk() is idempotent: INSERT OR IGNORE prevents duplicates.
  - delete_by_dataset() is atomic at the SQLite transaction level.
  - No foreign-key enforcement at the SQLite level (WAL mode for concurrency).
"""

import logging
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from nexus.memory._db import get_memory_db_path, ensure_memory_schema
from nexus.memory.chunker import Chunk

logger = logging.getLogger(__name__)


class MetadataStore:
    """
    Read/write interface for chunk text and metadata in SQLite.

    Thread safety: Each MetadataStore instance opens its own SQLite
    connection with WAL journal mode. Concurrent reads are safe.
    Concurrent writes serialise through SQLite's built-in locking.
    """

    def __init__(self):
        self._db_path = get_memory_db_path()
        ensure_memory_schema(self._db_path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=15)
        conn.row_factory = sqlite3.Row
        # WAL mode allows concurrent readers alongside a single writer.
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def save_chunk(self, chunk: Chunk) -> bool:
        """
        Persist a Chunk record. Idempotent via INSERT OR IGNORE.

        Returns:
            True  — chunk was newly inserted.
            False — chunk already existed (idempotent skip).
        """
        now = datetime.now(timezone.utc).isoformat()

        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT OR IGNORE INTO memory_chunks
                    (chunk_id, dataset_id, conversation_id, message_id,
                     chunk_index, role, timestamp, source, text,
                     token_count, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chunk.chunk_id,
                    chunk.dataset_id,
                    chunk.conversation_id,
                    chunk.message_id,
                    chunk.chunk_index,
                    chunk.role,
                    chunk.timestamp or "",
                    chunk.source,
                    chunk.text,
                    chunk.token_count,
                    now,
                ),
            )
            conn.commit()
            inserted = cur.rowcount > 0

        if not inserted:
            logger.debug(
                "[MetadataStore] chunk %s already exists — skipped.", chunk.chunk_id
            )

        return inserted

    def save_chunks_batch(self, chunks: List[Chunk]) -> int:
        """
        Persist multiple chunks in a single transaction.

        Returns:
            Number of newly inserted chunks (skips existing).
        """
        if not chunks:
            return 0

        now = datetime.now(timezone.utc).isoformat()
        rows = [
            (
                c.chunk_id,
                c.dataset_id,
                c.conversation_id,
                c.message_id,
                c.chunk_index,
                c.role,
                c.timestamp or "",
                c.source,
                c.text,
                c.token_count,
                now,
            )
            for c in chunks
        ]

        with self._connect() as conn:
            cur = conn.cursor()
            cur.executemany(
                """
                INSERT OR IGNORE INTO memory_chunks
                    (chunk_id, dataset_id, conversation_id, message_id,
                     chunk_index, role, timestamp, source, text,
                     token_count, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()
            inserted = cur.rowcount  # rows affected by last INSERT

        logger.debug(
            "[MetadataStore] Batch saved: %d chunks submitted, ~%d inserted.",
            len(chunks), inserted,
        )
        return inserted

    def delete_by_dataset(self, dataset_id: str) -> int:
        """
        Delete all chunks belonging to a dataset.
        Returns the number of rows deleted.
        """
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM memory_chunks WHERE dataset_id = ?", (dataset_id,)
            )
            conn.commit()
            count = cur.rowcount

        logger.info(
            "[MetadataStore] Deleted %d chunks for dataset %s.", count, dataset_id
        )
        return count

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get_chunk(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single chunk record by its ID.

        Returns:
            Dict with all chunk fields, or None if not found.
        """
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM memory_chunks WHERE chunk_id = ?", (chunk_id,)
            )
            row = cur.fetchone()

        return dict(row) if row else None

    def get_chunks_by_dataset(
        self,
        dataset_id: str,
        limit: int = 10000,
    ) -> List[Dict[str, Any]]:
        """
        Return all chunks for a dataset, ordered by conversation_id + chunk_index.
        Used for dataset rebuild and audit operations.
        """
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT * FROM memory_chunks
                WHERE dataset_id = ?
                ORDER BY conversation_id, message_id, chunk_index
                LIMIT ?
                """,
                (dataset_id, limit),
            )
            rows = cur.fetchall()

        return [dict(r) for r in rows]

    def get_chunks_by_ids(self, chunk_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Bulk-fetch multiple chunks by ID. Returns a dict keyed by chunk_id.
        Useful for hydrating search results.
        """
        if not chunk_ids:
            return {}

        placeholders = ",".join("?" * len(chunk_ids))
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                f"SELECT * FROM memory_chunks WHERE chunk_id IN ({placeholders})",
                chunk_ids,
            )
            rows = cur.fetchall()

        return {row["chunk_id"]: dict(row) for row in rows}

    def exists(self, chunk_id: str) -> bool:
        """Return True if a chunk with this ID is already stored."""
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT 1 FROM memory_chunks WHERE chunk_id = ? LIMIT 1",
                (chunk_id,),
            )
            return cur.fetchone() is not None

    def count_by_dataset(self, dataset_id: str) -> int:
        """Return the number of chunks stored for a given dataset."""
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM memory_chunks WHERE dataset_id = ?",
                (dataset_id,),
            )
            row = cur.fetchone()
        return row[0] if row else 0

    def total_count(self) -> int:
        """Return the total number of chunks across all datasets."""
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM memory_chunks")
            row = cur.fetchone()
        return row[0] if row else 0
