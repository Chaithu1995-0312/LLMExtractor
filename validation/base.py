"""
validation/base.py
==================
NexusValidator — Base class for all pipeline validation stages.

Design decisions aligned with your codebase:
  - Uses psycopg2 directly (same as run_l2_backfill.py) — no ORM overhead
  - Reads DATABASE_URL from environment (same .env used for PROD)
  - Errors are caught, logged, and execution CONTINUES (no --strict by default)
  - Latency is tracked in milliseconds
  - Security: TODO — add read-only audit credentials
  - CI/CD:    TODO — integrate with CI pipeline
"""

import os
import sys
import json
import time
import uuid
import platform
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from dotenv import load_dotenv
    _REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    load_dotenv(os.path.join(_REPO_ROOT, ".env"))
except ImportError:
    pass

import psycopg2
from psycopg2.extras import Json

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://nexus:nexus@localhost:5432/nexus")

# TODO: Security — use a separate read-only audit DB user/role instead of the
# main nexus credentials. For now, personal use / PROD uses same .env creds.


class NexusValidator:
    """
    Base validator that all stage validators inherit from.

    Usage:
        validator = NexusValidator(stage="L1", batch_id="batch_001")
        with validator:
            # ... do validation work ...
            validator.log("VALIDATION_START", {"source_count": 100})
    """

    def __init__(
        self,
        stage: str = "PRE",
        batch_id: Optional[str] = None,
        strict: bool = False,
    ):
        """
        Args:
            stage:    One of 'PRE', 'L1', 'L2', 'L3', 'POST'
            batch_id: Identifier for this validation run (auto-generated if None)
            strict:   If True, validation failures raise exceptions.
                      Default False — log and continue.
                      TODO: CI/CD — set strict=True in pipeline runs.
        """
        self.stage = stage
        self.batch_id = batch_id or f"val-{str(uuid.uuid4())[:12]}"
        self.strict = strict
        self._conn: Optional[psycopg2.extensions.connection] = None
        self._in_context = False

        # In-memory audit log (mirrored to DB when available)
        self.audit_log: List[Dict[str, Any]] = []
        self.error_count: int = 0
        self.warning_count: int = 0

    # ------------------------------------------------------------------
    # Context manager — opens / closes a single DB connection per run
    # ------------------------------------------------------------------

    def __enter__(self):
        self._open_db()
        self._in_context = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._close_db()
        self._in_context = False
        # Never suppress exceptions
        return False

    def _open_db(self):
        try:
            self._conn = psycopg2.connect(DATABASE_URL)
            self._conn.autocommit = True
        except Exception as e:
            # DB unavailable — fall back to in-memory only logging
            print(f"[NexusValidator] WARN: Cannot connect to DB for audit trail: {e}")
            self._conn = None

    def _close_db(self):
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    # ------------------------------------------------------------------
    # Core logging
    # ------------------------------------------------------------------

    def log(
        self,
        event_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        status: str = "ok",
        latency_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Append an audit event to the in-memory log AND persist to
        audit.processing_trail (if DB is available).

        Args:
            event_type:  Short string identifier, e.g. 'SPLIT_START'
            metadata:    Arbitrary JSON-serialisable dict
            status:      'ok' | 'warn' | 'error'
            latency_ms:  Processing duration in milliseconds

        Returns:
            The event dict that was logged.
        """
        event: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "batch_id": self.batch_id,
            "stage": self.stage,
            "event_type": event_type,
            "status": status,
            "latency_ms": latency_ms,
            "system": {
                "host": platform.node(),
                "python": sys.version.split()[0],
            },
            **(metadata or {}),
        }

        self.audit_log.append(event)

        if status == "error":
            self.error_count += 1
        elif status == "warn":
            self.warning_count += 1

        # Print to stdout (legacy tooling compatibility, same as GraphManager)
        print(f"[AUDIT:{self.stage}] {event_type} | status={status}"
              + (f" | {latency_ms}ms" if latency_ms is not None else ""))

        # Persist to DB (non-fatal if unavailable)
        self._persist_to_db(event_type, status, latency_ms, metadata)

        return event

    def log_error(self, event_type: str, error: Exception, metadata: Optional[Dict] = None):
        """Convenience wrapper for error events. Logs and continues (never re-raises)."""
        meta = {**(metadata or {}), "error": str(error)}
        self.log(event_type, meta, status="error")

    def log_timed(self, event_type: str, start_time: float, metadata: Optional[Dict] = None, status: str = "ok"):
        """Log an event with auto-computed latency from a start time (time.time())."""
        latency_ms = int((time.time() - start_time) * 1000)
        self.log(event_type, metadata, status=status, latency_ms=latency_ms)

    # ------------------------------------------------------------------
    # DB persistence
    # ------------------------------------------------------------------

    def _persist_to_db(
        self,
        event_type: str,
        status: str,
        latency_ms: Optional[int],
        metadata: Optional[Dict],
    ):
        """Write event to audit.processing_trail. Non-fatal on any error."""
        if not self._conn:
            return
        try:
            with self._conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO audit.processing_trail
                        (batch_id, stage, event_type, status, latency_ms, created_at, metadata)
                    VALUES (%s, %s, %s, %s, %s, NOW(), %s)
                    """,
                    (
                        self.batch_id,
                        self.stage,
                        event_type,
                        status,
                        latency_ms,
                        Json(metadata or {}),
                    ),
                )
        except Exception as e:
            # DB audit failure must never disrupt the calling pipeline
            print(f"[NexusValidator] WARN: Failed to persist audit event '{event_type}': {e}")

    # ------------------------------------------------------------------
    # Summary helpers
    # ------------------------------------------------------------------

    def summary(self) -> Dict[str, Any]:
        """Return a summary of this validation run."""
        return {
            "batch_id": self.batch_id,
            "stage": self.stage,
            "total_events": len(self.audit_log),
            "errors": self.error_count,
            "warnings": self.warning_count,
            "passed": self.error_count == 0,
        }

    def assert_no_errors(self):
        """
        Raise if there were errors AND strict=True.
        In non-strict mode (default) just prints a warning.
        """
        if self.error_count > 0:
            msg = (
                f"[NexusValidator] Validation stage '{self.stage}' completed with "
                f"{self.error_count} error(s). Check audit trail for batch_id='{self.batch_id}'."
            )
            if self.strict:
                raise RuntimeError(msg)
            else:
                print(f"WARN: {msg}")

    # ------------------------------------------------------------------
    # Watermarking helper (attaches _audit metadata to any data dict)
    # ------------------------------------------------------------------

    @staticmethod
    def apply_watermark(data: Dict[str, Any], stage: str) -> Dict[str, Any]:
        """
        Attach a non-intrusive _audit metadata block to any data dict.
        Used to trace provenance through the pipeline.

        # TODO: Security — strip watermarks before external API calls.
        """
        return {
            **data,
            "_audit": {
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "stage": stage,
                "stage_versions": {
                    "l1_extractor": "1.0.2",
                    "l2_synthesizer": "0.9.1",
                    "l3_clusterer": "2.1.0",
                },
                "environment": {
                    "host": platform.node(),
                    "python": sys.version.split()[0],
                },
            },
        }
