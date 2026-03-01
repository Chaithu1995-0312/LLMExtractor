"""
nexus.memory.dataset_manager
=============================
Manages versioned MemoryDataset records for the Memory Layer.

A dataset groups all chunks produced from a single ingestion run. Each dataset
is identified by a UUID, carries the embedding model that was used, and supports
rebuild, clear, and switch operations.

Storage: SQLite via the memory-layer's own DB (data/memory_layer.db).
This is intentionally separate from the Nexus Postgres instance so the Memory
Layer can operate independently.

Invariants:
- dataset_id is a UUID generated at creation time.
- dataset_version monotonically increments per source file.
- Rebuild does NOT delete the old dataset record; it creates a new version.
- Clear wipes all chunks associated with a dataset_id but retains the record.
"""

import sqlite3
import uuid
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from nexus.memory._db import get_memory_db_path, ensure_memory_schema

logger = logging.getLogger(__name__)


@dataclass
class MemoryDataset:
    """Represents one ingestion run against a ChatGPT export file."""

    dataset_id: str
    """UUID string — primary key."""

    dataset_version: int
    """Monotonically incrementing version for the same source."""

    embedding_model: str
    """Ollama model used for embedding (e.g., 'nomic-embed-text')."""

    source_filename: str
    """Original filename of the ChatGPT export JSON."""

    status: str
    """One of: PENDING | RUNNING | COMPLETE | FAILED | CLEARED."""

    total_chunks: int = 0
    """Number of chunks successfully indexed."""

    total_conversations: int = 0
    """Number of conversations parsed from the export."""

    error_message: Optional[str] = None
    """Non-null only when status == FAILED."""

    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DatasetManager:
    """
    CRUD interface for MemoryDataset records.

    All operations are backed by the memory-layer SQLite DB.
    The class is NOT a singleton — callers may instantiate freely; the DB
    file acts as the shared serialisation point.
    """

    def __init__(self):
        self._db_path = get_memory_db_path()
        ensure_memory_schema(self._db_path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def _row_to_dataset(self, row: sqlite3.Row) -> MemoryDataset:
        return MemoryDataset(
            dataset_id=row["dataset_id"],
            dataset_version=row["dataset_version"],
            embedding_model=row["embedding_model"],
            source_filename=row["source_filename"],
            status=row["status"],
            total_chunks=row["total_chunks"],
            total_conversations=row["total_conversations"],
            error_message=row["error_message"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_dataset(
        self,
        source_filename: str,
        embedding_model: str = "nomic-embed-text",
    ) -> MemoryDataset:
        """
        Create a new dataset record for a given source file.

        If a prior dataset exists for the same filename, the new dataset
        receives version = max(existing_version) + 1. Otherwise version = 1.
        """
        dataset_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        with self._connect() as conn:
            cur = conn.cursor()

            # Determine next version for this source file.
            cur.execute(
                "SELECT MAX(dataset_version) FROM memory_datasets WHERE source_filename = ?",
                (source_filename,),
            )
            row = cur.fetchone()
            max_ver = row[0] if row[0] is not None else 0
            next_version = max_ver + 1

            cur.execute(
                """
                INSERT INTO memory_datasets
                    (dataset_id, dataset_version, embedding_model, source_filename,
                     status, total_chunks, total_conversations, error_message,
                     created_at, updated_at)
                VALUES (?, ?, ?, ?, 'PENDING', 0, 0, NULL, ?, ?)
                """,
                (dataset_id, next_version, embedding_model, source_filename, now, now),
            )
            conn.commit()

        logger.info(
            "[DatasetManager] Created dataset %s v%d for '%s'",
            dataset_id,
            next_version,
            source_filename,
        )

        return self.get_dataset(dataset_id)  # type: ignore[return-value]

    def get_dataset(self, dataset_id: str) -> Optional[MemoryDataset]:
        """Return a MemoryDataset by its UUID, or None if not found."""
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM memory_datasets WHERE dataset_id = ?", (dataset_id,)
            )
            row = cur.fetchone()
        return self._row_to_dataset(row) if row else None

    def get_latest_dataset(self, source_filename: str) -> Optional[MemoryDataset]:
        """Return the most recent COMPLETE dataset for a source file."""
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT * FROM memory_datasets
                WHERE source_filename = ? AND status = 'COMPLETE'
                ORDER BY dataset_version DESC
                LIMIT 1
                """,
                (source_filename,),
            )
            row = cur.fetchone()
        return self._row_to_dataset(row) if row else None

    def list_datasets(self) -> List[MemoryDataset]:
        """Return all datasets ordered by creation time descending."""
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM memory_datasets ORDER BY created_at DESC"
            )
            rows = cur.fetchall()
        return [self._row_to_dataset(r) for r in rows]

    def update_status(
        self,
        dataset_id: str,
        status: str,
        total_chunks: Optional[int] = None,
        total_conversations: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Update dataset status and optional counters.

        Called by MemoryService during the ingestion lifecycle:
          PENDING -> RUNNING -> COMPLETE | FAILED
        """
        now = datetime.now(timezone.utc).isoformat()

        with self._connect() as conn:
            cur = conn.cursor()

            # Build SET clause dynamically.
            fields: Dict[str, Any] = {"status": status, "updated_at": now}
            if total_chunks is not None:
                fields["total_chunks"] = total_chunks
            if total_conversations is not None:
                fields["total_conversations"] = total_conversations
            if error_message is not None:
                fields["error_message"] = error_message

            set_clause = ", ".join(f"{k} = ?" for k in fields)
            params = list(fields.values()) + [dataset_id]
            cur.execute(
                f"UPDATE memory_datasets SET {set_clause} WHERE dataset_id = ?",
                params,
            )
            conn.commit()

        logger.info(
            "[DatasetManager] Dataset %s -> status=%s chunks=%s",
            dataset_id,
            status,
            total_chunks,
        )

    def clear_dataset(self, dataset_id: str) -> None:
        """
        Mark a dataset as CLEARED and signal MetadataStore to wipe its chunks.

        This does NOT delete the dataset record — lineage is preserved.
        The actual chunk deletion is handled by MetadataStore and
        ChromaMemoryVectorStore separately (called by MemoryService).
        """
        self.update_status(dataset_id, status="CLEARED")
        logger.info("[DatasetManager] Dataset %s marked as CLEARED.", dataset_id)

    def delete_dataset_record(self, dataset_id: str) -> None:
        """
        Hard-delete the dataset record (admin / test use only).
        Does NOT cascade to chunks — call MetadataStore.delete_by_dataset() first.
        """
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM memory_datasets WHERE dataset_id = ?", (dataset_id,)
            )
            conn.commit()
        logger.warning("[DatasetManager] Hard-deleted dataset record %s.", dataset_id)
