"""
nexus.memory._db
================
Internal DB bootstrap for the Memory Layer.

Provides a single SQLite file (data/memory_layer.db) that is owned exclusively
by the Memory Layer. No other Nexus module reads or writes this file.

Schema tables:
  memory_datasets  — MemoryDataset records (versioned ingestion runs)
  memory_chunks    — chunk text + full metadata for retrieval hydration

The ChromaDB vector index is managed separately in data/memory_chroma/.
"""

import os
import sqlite3
import logging

logger = logging.getLogger(__name__)

# Resolve path relative to repo root (two levels above this file's package).
_THIS_FILE = os.path.abspath(__file__)
_PACKAGE_DIR = os.path.dirname(_THIS_FILE)        # src/nexus/memory/
_SRC_DIR = os.path.dirname(_PACKAGE_DIR)           # src/nexus/
_NEXUS_PKG = os.path.dirname(_SRC_DIR)             # src/
_REPO_ROOT = os.path.dirname(_NEXUS_PKG)           # repo root

_DATA_DIR = os.path.join(_REPO_ROOT, "data")
_MEMORY_DB_FILENAME = "memory_layer.db"
_CHROMA_DIR = os.path.join(_DATA_DIR, "memory_chroma")


def get_memory_db_path() -> str:
    """Return the absolute path for the memory-layer SQLite file."""
    os.makedirs(_DATA_DIR, exist_ok=True)
    return os.path.join(_DATA_DIR, _MEMORY_DB_FILENAME)


def get_chroma_persist_dir() -> str:
    """Return the directory ChromaDB should persist its files to."""
    os.makedirs(_CHROMA_DIR, exist_ok=True)
    return _CHROMA_DIR


# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """
-- Dataset registry
CREATE TABLE IF NOT EXISTS memory_datasets (
    dataset_id          TEXT PRIMARY KEY,
    dataset_version     INTEGER NOT NULL DEFAULT 1,
    embedding_model     TEXT NOT NULL,
    source_filename     TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'PENDING',
    total_chunks        INTEGER NOT NULL DEFAULT 0,
    total_conversations INTEGER NOT NULL DEFAULT 0,
    error_message       TEXT,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_datasets_source
    ON memory_datasets (source_filename, dataset_version DESC);

CREATE INDEX IF NOT EXISTS idx_datasets_status
    ON memory_datasets (status);

-- Chunk text + metadata (vector IDs are the chunk_id stored in ChromaDB)
CREATE TABLE IF NOT EXISTS memory_chunks (
    chunk_id            TEXT PRIMARY KEY,
    dataset_id          TEXT NOT NULL,
    conversation_id     TEXT NOT NULL,
    message_id          TEXT NOT NULL,
    chunk_index         INTEGER NOT NULL,
    role                TEXT NOT NULL,
    timestamp           TEXT,
    source              TEXT NOT NULL DEFAULT 'chatgpt_export',
    text                TEXT NOT NULL,
    token_count         INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT NOT NULL,
    FOREIGN KEY (dataset_id) REFERENCES memory_datasets(dataset_id)
);

CREATE INDEX IF NOT EXISTS idx_chunks_dataset
    ON memory_chunks (dataset_id);

CREATE INDEX IF NOT EXISTS idx_chunks_conversation
    ON memory_chunks (conversation_id);
"""


def ensure_memory_schema(db_path: str) -> None:
    """
    Idempotently apply the memory-layer DDL to the given SQLite file.
    Safe to call on every startup — all statements use IF NOT EXISTS.
    """
    try:
        conn = sqlite3.connect(db_path, timeout=15)
        conn.executescript(_SCHEMA_SQL)
        conn.commit()
        conn.close()
        logger.debug("[MemoryDB] Schema ensured at %s", db_path)
    except Exception as exc:
        logger.error("[MemoryDB] Schema bootstrap failed: %s", exc)
        raise
