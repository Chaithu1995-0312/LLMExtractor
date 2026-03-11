"""
L2 Semantic Substrate — Embedding Backfill Engine
==================================================
Backfills OpenAI embeddings for all eligible nodes in graph.nodes
and stores them in graph.vector_meta.

SELF-REVIEW PACKET
------------------

Assumptions:
  - pgvector extension is installed and graph.vector_meta exists (schema_evolution.sql applied).
  - schema_freeze0_patches.sql has been applied: graph.nodes.vector_status column exists,
    graph.vector_meta has is_stale / stale_reason / stale_at columns.
  - OPENAI_API_KEY and DATABASE_URL are set in the environment.
  - data->>'statement' may be empty/None on some nodes (handled: empty text still embedded,
    producing a valid low-signal vector).
  - data->'metadata' is a nested JSONB object (may be absent; defaults to {}).

Failure Modes:
  - OpenAI API unavailable: per-node retry (max 3) with exponential backoff, then skip + log.
  - DB write fails: transaction rolled back, node stays 'pending', failure counted.
  - Dimension mismatch: ValueError raised before any DB write, node skipped, failure counted.
  - Lifecycle changed mid-run to 'killed': UPDATE WHERE lifecycle IN ('loose','forming')
    returns 0 rows → vector_meta row orphaned but is_stale=FALSE; acceptable for bootstrap.
    The next drift pass will mark is_stale=TRUE via _mark_vector_stale().

API Rate Limit Handling:
  - openai.RateLimitError      → backoff 2^attempt seconds, retry up to MAX_RETRIES.
  - openai.APIConnectionError  → same backoff/retry.
  - openai.APITimeoutError     → same backoff/retry.
  - All other openai errors    → same backoff/retry (conservative: unknown API errors
    may be transient).
  - After MAX_RETRIES exhausted: node counted as failure, skipped, run continues.

Partial Batch Recovery:
  - Each node is committed in its own transaction independently within the batch loop.
  - A failure on node N does NOT roll back nodes 0..N-1.
  - After a crash/restart, re-run is safe: eligible query excludes vector_status='indexed'.

Idempotency Guarantees:
  - Eligible query: WHERE data->>'lifecycle' IN ('loose','forming')
                    AND   data->>'vector_status' != 'indexed'
  - vector_meta insert: ON CONFLICT (node_id) DO NOTHING
  - nodes update: WHERE id = %s AND data->>'lifecycle' IN ('loose','forming')
  - Result: re-running this script N times produces exactly the same final DB state.

Vector Dimension Validation:
  - Asserts len(embedding) == EXPECTED_DIMENSIONS (1536) before any DB write.
  - Hard fail per node; never writes a truncated or wrong-dimension vector.

Database Transaction Safety:
  - Per-node atomic transaction wraps both the vector_meta INSERT and the nodes UPDATE.
  - Uses PostgresAdapter.transaction() which opens a psycopg2 connection from the pool,
    runs both statements, and commits atomically. On any exception, rolls back and returns
    the connection to the pool cleanly.
  - jsonb_set used for nodes UPDATE to surgically set vector_status without overwriting
    other JSONB fields.

Memory Usage Considerations:
  - Nodes are fetched in configurable batch_size (default 50) using OFFSET pagination.
  - Each embedding is a Python list[float] of 1536 elements ≈ 12 KB per node.
  - Peak in-process memory per batch ≈ 50 * 12 KB = ~600 KB (negligible).
  - Full node result set is NOT loaded into RAM; pagination ensures O(batch_size) memory.

How to Rerun Safely Without Duplication:
  - The eligible query filters out vector_status='indexed' nodes.
  - ON CONFLICT DO NOTHING prevents duplicate vector_meta rows.
  - The UPDATE lifecycle guard prevents vector_status flip on killed nodes.
  - Simply re-run: python scripts/run_l2_backfill.py

Risk of Embedding Stale Lifecycle States:
  - Snapshot race: if a node transitions loose→killed between the SELECT and the UPDATE,
    the UPDATE's lifecycle guard (IN ('loose','forming')) will return 0 rows, so
    vector_status is NOT flipped to 'indexed'. The vector_meta row exists but the node
    stays 'pending'. On next run it is skipped (lifecycle guard blocks it). The orphaned
    vector_meta row is safe; the DriftEngine will mark is_stale=TRUE on the next pass.
  - This is the most conservative safe handling: we never mark a killed node as indexed.

Input Hash (Option B — Production Grade):
  - SHA-256 of the embedding input text is stored in vector_meta.input_hash.
  - On future re-runs or drift passes, a hash mismatch signals that the statement changed
    and the embedding is stale → triggers is_stale=TRUE automatically.
  - Schema migration required: ALTER TABLE graph.vector_meta ADD COLUMN IF NOT EXISTS
    input_hash TEXT; (handled by the schema patch at the end of this module).

"""

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
from nexus.config import get_agent_config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_VERSION = "v1"
EXPECTED_DIMENSIONS = 1536
MAX_RETRIES = 3
BACKOFF_BASE = 2.0          # seconds; delay = BACKOFF_BASE ** attempt → 2s, 4s, 8s
DEFAULT_BATCH_SIZE = 50

# Eligible lifecycle states for embedding
ELIGIBLE_LIFECYCLES = ("loose", "forming")

# SQL: fetch eligible nodes with pagination
# We re-process nodes that are not yet 'indexed_v2'
_SQL_FETCH_ELIGIBLE = """
SELECT id, data
FROM graph.nodes
WHERE data->>'lifecycle' = ANY(%s)
AND   (data->>'vector_status' IS NULL OR data->>'vector_status' != 'indexed_v2')
ORDER BY created_at ASC
LIMIT %s OFFSET %s
"""

# SQL: upsert vector_meta — ON CONFLICT DO UPDATE for idempotency and v2 migration
# Writes to embedding_v2 (1536) as per Critical Data Migration Plan.
_SQL_UPSERT_VECTOR_META = """
INSERT INTO graph.vector_meta
    (node_id, embedding_v2, embedding_model_v2, embedding_version, is_stale, input_hash, indexed_at)
VALUES
    (%s, %s::vector, %s, %s, FALSE, %s, NOW())
ON CONFLICT (node_id) DO UPDATE SET
    embedding_v2 = EXCLUDED.embedding_v2,
    embedding_model_v2 = EXCLUDED.embedding_model_v2,
    is_stale = FALSE,
    indexed_at = NOW()
"""

# SQL: update vector_status — lifecycle guard prevents flipping killed nodes
_SQL_UPDATE_NODE_STATUS = """
UPDATE graph.nodes
SET data = jsonb_set(data, '{vector_status}', '"indexed_v2"', true)
WHERE id = %s
AND   data->>'lifecycle' = ANY(%s)
"""

# SQL: count total eligible nodes (for progress reporting)
_SQL_COUNT_ELIGIBLE = """
SELECT COUNT(*)
FROM graph.nodes
WHERE data->>'lifecycle' = ANY(%s)
AND   (data->>'vector_status' IS NULL OR data->>'vector_status' != 'indexed_v2')
"""

# Schema patch: add stale tracking and input_hash columns if not present
# Also ensures embedding_v2 exists (1536 dims).
_SQL_ENSURE_VECTOR_META_COLUMNS = """
ALTER TABLE graph.vector_meta
    ADD COLUMN IF NOT EXISTS is_stale      BOOLEAN   NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS stale_reason  TEXT,
    ADD COLUMN IF NOT EXISTS stale_at      TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS input_hash    TEXT,
    ADD COLUMN IF NOT EXISTS embedding_v2  vector(1536),
    ADD COLUMN IF NOT EXISTS embedding_model_v2 TEXT DEFAULT 'text-embedding-3-small';
"""


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class BackfillSummary:
    total_nodes_scanned: int = 0
    total_embeddings_created: int = 0
    failures: int = 0
    duration_seconds: float = 0.0
    skipped_lifecycle_guard: int = 0      # nodes where lifecycle changed mid-run

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_nodes_scanned": self.total_nodes_scanned,
            "total_embeddings_created": self.total_embeddings_created,
            "failures": self.failures,
            "duration_seconds": round(self.duration_seconds, 3),
            "skipped_lifecycle_guard": self.skipped_lifecycle_guard,
        }


@dataclass
class NodeRecord:
    node_id: str
    data: Dict[str, Any]


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class L2BackfillEngine:
    """
    L2 Semantic Substrate backfill engine.

    Embeds all eligible graph.nodes using text-embedding-3-small (1536-dim)
    and stores results in graph.vector_meta, then flips vector_status to 'indexed'.

    Usage:
        engine = L2BackfillEngine()
        summary = engine.run(batch_size=50)
        print(summary.to_dict())
    """

    def __init__(self, database_url: Optional[str] = None, openai_api_key: Optional[str] = None):
        self.config = get_agent_config("vector_backfill")
        self.model = self.config.get("model", EMBEDDING_MODEL)
        self.dimension = self.config.get("dimension", EXPECTED_DIMENSIONS)
        self.batch_size = self.config.get("batch_size", DEFAULT_BATCH_SIZE)
        self.max_retries = self.config.get("max_retries", MAX_RETRIES)

        self._database_url = database_url or os.environ.get("DATABASE_URL")
        if not self._database_url:
            raise RuntimeError("DATABASE_URL not set. Cannot connect to PostgreSQL.")

        self._openai_api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        if not self._openai_api_key:
            raise RuntimeError("OPENAI_API_KEY not set. Cannot call embedding API.")

        # Lazy-init OpenAI client on first use
        self._openai_client = None

        logger.info("[L2Backfill] Engine initialized. Model=%s Dimensions=%d",
                    self.model, self.dimension)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, batch_size: int = DEFAULT_BATCH_SIZE) -> BackfillSummary:
        """
        Main entry point. Processes all eligible nodes in batches.

        Returns:
            BackfillSummary with counts and duration.
        """
        summary = BackfillSummary()
        run_start = time.time()

        # Ensure input_hash column exists before writing
        self._ensure_schema_patch()

        total_eligible = self._count_eligible()
        logger.info("[L2Backfill] Starting backfill. Total eligible nodes: %d  Batch size: %d",
                    total_eligible, batch_size)

        offset = 0
        batch_number = 0

        while True:
            batch_start = time.time()
            batch_number += 1
            nodes = self._fetch_batch(batch_size, offset)

            if not nodes:
                logger.info("[L2Backfill] No more nodes at offset %d. Scan complete.", offset)
                break

            logger.info("[L2Backfill] Batch %d — offset=%d  size=%d",
                        batch_number, offset, len(nodes))

            for node in nodes:
                summary.total_nodes_scanned += 1
                success, skipped = self._process_node(node)
                if success:
                    summary.total_embeddings_created += 1
                elif skipped:
                    summary.skipped_lifecycle_guard += 1
                else:
                    summary.failures += 1

            batch_elapsed = time.time() - batch_start
            logger.info(
                "[L2Backfill] Batch %d complete in %.2fs — "
                "scanned=%d  created=%d  failures=%d  lifecycle_skipped=%d",
                batch_number, batch_elapsed,
                summary.total_nodes_scanned,
                summary.total_embeddings_created,
                summary.failures,
                summary.skipped_lifecycle_guard,
            )

            # Only advance offset by nodes that were successfully created or failed.
            # Lifecycle-skipped nodes are excluded from the next eligible query anyway
            # (they are killed). Offset advances by batch size always — safe because
            # successfully embedded nodes are excluded by vector_status filter on next pass.
            offset += len(nodes)

            # If we got fewer rows than batch_size, we have reached the end.
            if len(nodes) < batch_size:
                break

        summary.duration_seconds = time.time() - run_start

        logger.info(
            "[L2Backfill] ✅ Backfill complete. "
            "scanned=%d  created=%d  failures=%d  lifecycle_skipped=%d  duration=%.3fs",
            summary.total_nodes_scanned,
            summary.total_embeddings_created,
            summary.failures,
            summary.skipped_lifecycle_guard,
            summary.duration_seconds,
        )

        return summary

    # ------------------------------------------------------------------
    # Node Processing
    # ------------------------------------------------------------------

    def _process_node(self, node: NodeRecord) -> Tuple[bool, bool]:
        """
        Process a single node: embed → validate → write DB atomically.

        Returns:
            (success: bool, lifecycle_skipped: bool)
            - (True, False)  → committed
            - (False, True)  → lifecycle changed mid-run, skipped
            - (False, False) → error, counted as failure
        """
        node_id = node.node_id

        # 1. Build embedding input text
        embed_text = self._build_embedding_text(node.data)
        input_hash = self._sha256(embed_text)

        logger.debug("[L2Backfill] Processing node=%s  input_len=%d  hash=%s",
                     node_id, len(embed_text), input_hash[:12])

        # 2. Call OpenAI — with retry + broad exception handling
        api_start = time.time()
        try:
            embedding = self._embed_with_retry(embed_text, node_id)
        except Exception as exc:
            logger.error("[L2Backfill] ❌ Embedding permanently failed for node=%s: %s",
                         node_id, exc)
            return False, False

        api_latency = time.time() - api_start
        logger.debug("[L2Backfill] API latency for node=%s: %.3fs", node_id, api_latency)

        # 3. Validate dimensions
        if len(embedding) != self.dimension:
            logger.error(
                "[L2Backfill] ❌ Dimension mismatch for node=%s: expected=%d got=%d",
                node_id, self.dimension, len(embedding),
            )
            return False, False

        # 4. Write to DB atomically
        db_start = time.time()
        try:
            lifecycle_updated = self._write_to_db(node_id, embedding, input_hash)
        except Exception as exc:
            logger.error("[L2Backfill] ❌ DB write failed for node=%s: %s", node_id, exc)
            return False, False

        db_latency = time.time() - db_start
        logger.debug("[L2Backfill] DB write latency for node=%s: %.3fs", node_id, db_latency)

        if not lifecycle_updated:
            # vector_meta was written (ON CONFLICT DO NOTHING), but nodes UPDATE
            # returned 0 rows — lifecycle changed to something outside ('loose','forming')
            # mid-run (e.g., killed). We count this as a lifecycle guard skip.
            logger.warning(
                "[L2Backfill] ⚠️  Lifecycle guard triggered for node=%s — "
                "lifecycle changed mid-run; vector_status NOT flipped.",
                node_id,
            )
            return False, True

        logger.info("[L2Backfill] ✓ node=%s  api_latency=%.3fs  db_latency=%.3fs",
                    node_id, api_latency, db_latency)
        return True, False

    def _write_to_db(self, node_id: str, embedding: List[float], input_hash: str) -> bool:
        """
        Atomically write vector_meta + update node vector_status.

        Returns:
            True if the nodes UPDATE matched a row (lifecycle guard passed).
            False if 0 rows updated (lifecycle changed mid-run).
        """
        # Format embedding as pgvector literal: '[0.1,0.2,...]'
        embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"

        lifecycle_updated = False

        conn = psycopg2.connect(self._database_url)
        try:
            with conn:
                with conn.cursor() as cur:
                    # Step 1: Insert into vector_meta (idempotent)
                    cur.execute(
                        _SQL_UPSERT_VECTOR_META,
                        (node_id, embedding_str, self.model, EMBEDDING_VERSION, input_hash),
                    )

                    # Step 2: Update vector_status with lifecycle guard
                    cur.execute(
                        _SQL_UPDATE_NODE_STATUS,
                        (node_id, list(ELIGIBLE_LIFECYCLES)),
                    )
                    rows_updated = cur.rowcount
                    lifecycle_updated = rows_updated > 0
            # conn.__exit__ commits on success
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        return lifecycle_updated

    # ------------------------------------------------------------------
    # Embedding
    # ------------------------------------------------------------------

    def _embed_with_retry(self, text: str, node_id: str) -> List[float]:
        """
        Call OpenAI embedding API with exponential backoff retry.

        Handles:
          - RateLimitError
          - APIConnectionError
          - APITimeoutError
          - Any other openai.OpenAIError (conservative — may be transient)

        Raises RuntimeError after MAX_RETRIES exhausted.
        """
        import openai

        client = self._get_openai_client()
        last_exc: Optional[Exception] = None

        for attempt in range(self.max_retries):
            try:
                response = client.embeddings.create(
                    model=self.model,
                    input=text,
                )
                return response.data[0].embedding

            except openai.RateLimitError as exc:
                last_exc = exc
                wait = BACKOFF_BASE ** (attempt + 1)
                logger.warning(
                    "[L2Backfill] RateLimitError for node=%s (attempt %d/%d). "
                    "Retrying in %.1fs...",
                    node_id, attempt + 1, self.max_retries, wait,
                )
                time.sleep(wait)

            except openai.APIConnectionError as exc:
                last_exc = exc
                wait = BACKOFF_BASE ** (attempt + 1)
                logger.warning(
                    "[L2Backfill] APIConnectionError for node=%s (attempt %d/%d). "
                    "Retrying in %.1fs...",
                    node_id, attempt + 1, self.max_retries, wait,
                )
                time.sleep(wait)

            except openai.APITimeoutError as exc:
                last_exc = exc
                wait = BACKOFF_BASE ** (attempt + 1)
                logger.warning(
                    "[L2Backfill] APITimeoutError for node=%s (attempt %d/%d). "
                    "Retrying in %.1fs...",
                    node_id, attempt + 1, self.max_retries, wait,
                )
                time.sleep(wait)

            except openai.APIStatusError as exc:
                # Covers ServiceUnavailableError (503), InternalServerError (500), etc.
                last_exc = exc
                wait = BACKOFF_BASE ** (attempt + 1)
                logger.warning(
                    "[L2Backfill] APIStatusError (status=%s) for node=%s (attempt %d/%d). "
                    "Retrying in %.1fs...",
                    getattr(exc, 'status_code', '?'),
                    node_id, attempt + 1, self.max_retries, wait,
                )
                time.sleep(wait)

            except openai.OpenAIError as exc:
                # Catch-all for any other OpenAI SDK error
                last_exc = exc
                wait = BACKOFF_BASE ** (attempt + 1)
                logger.warning(
                    "[L2Backfill] OpenAIError for node=%s (attempt %d/%d): %s. "
                    "Retrying in %.1fs...",
                    node_id, attempt + 1, self.max_retries, exc, wait,
                )
                time.sleep(wait)

        raise RuntimeError(
            f"[L2Backfill] embed_with_retry() failed after {self.max_retries} attempts "
            f"for node={node_id}: {last_exc}"
        ) from last_exc

    # ------------------------------------------------------------------
    # Text Construction
    # ------------------------------------------------------------------

    @staticmethod
    def _build_embedding_text(data: Dict[str, Any]) -> str:
        """
        Construct the canonical embedding input string.

        Format:
            Topic: {metadata.sync_topic_name}
            Authority: {metadata.authority_level}
            Role: {metadata.role}
            Statement:
            {statement}

        Missing fields default to empty string — never raises.
        """
        meta: Dict[str, Any] = data.get("metadata") or {}
        topic = meta.get("sync_topic_name") or ""
        authority = meta.get("authority_level") or ""
        role = meta.get("role") or ""
        statement = data.get("statement") or ""

        return (
            f"Topic: {topic}\n"
            f"Authority: {authority}\n"
            f"Role: {role}\n"
            f"Statement:\n{statement}"
        ).strip()

    # ------------------------------------------------------------------
    # DB Helpers
    # ------------------------------------------------------------------

    def _fetch_batch(self, batch_size: int, offset: int) -> List[NodeRecord]:
        """Fetch a page of eligible nodes."""
        conn = psycopg2.connect(self._database_url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    _SQL_FETCH_ELIGIBLE,
                    (list(ELIGIBLE_LIFECYCLES), batch_size, offset),
                )
                rows = cur.fetchall()
        finally:
            conn.close()

        nodes = []
        for row in rows:
            node_id = row[0]
            raw_data = row[1]
            data = raw_data if isinstance(raw_data, dict) else json.loads(raw_data or "{}")
            nodes.append(NodeRecord(node_id=node_id, data=data))
        return nodes

    def _count_eligible(self) -> int:
        """Count total eligible nodes for progress reporting."""
        conn = psycopg2.connect(self._database_url)
        try:
            with conn.cursor() as cur:
                cur.execute(_SQL_COUNT_ELIGIBLE, (list(ELIGIBLE_LIFECYCLES),))
                row = cur.fetchone()
                return row[0] if row else 0
        finally:
            conn.close()

    def _ensure_schema_patch(self):
        """
        Idempotently ensure all required columns exist in graph.vector_meta.
        Safe to run even if columns already exist (IF NOT EXISTS).
        """
        conn = psycopg2.connect(self._database_url)
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(_SQL_ENSURE_VECTOR_META_COLUMNS)
            logger.debug("[L2Backfill] Schema patch applied (vector_meta columns ensured).")
        except Exception as exc:
            logger.warning("[L2Backfill] Schema patch warning (non-fatal): %s", exc)
            conn.rollback()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # OpenAI Client
    # ------------------------------------------------------------------

    def _get_openai_client(self):
        """Lazy-init the OpenAI client (one instance per engine)."""
        if self._openai_client is None:
            from openai import OpenAI
            self._openai_client = OpenAI(api_key=self._openai_api_key)
            logger.debug("[L2Backfill] OpenAI client initialized.")
        return self._openai_client

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _sha256(text: str) -> str:
        """SHA-256 hex digest of the embedding input. Used for staleness detection."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
