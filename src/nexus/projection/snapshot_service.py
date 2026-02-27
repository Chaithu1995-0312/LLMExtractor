"""
Snapshot Service — Nexus Cognitive Operating System v1.0
=========================================================

Wraps DocumentCompiler to provide deterministic versioning of topic documents.

RESPONSIBILITIES
----------------
1. Compile a topic document via DocumentCompiler (READ-ONLY on the graph).
2. Compare the resulting hash against the latest persisted snapshot.
3. If changed (or no prior snapshot), bump the version and persist.
4. Return the StructuredDocument with the correct version attached.

VERSION BUMP RULES (spec §6.2)
-------------------------------
- First snapshot ever           → "1.0.0"
- Same hash as previous         → no write; return existing version.
- delta_sections == 0           → patch bump (x.y.z+1)
- abs(delta_sections) <= 3      → minor bump (x.y+1.0)
- abs(delta_sections) > 3       → major bump (x+1.0.0)

INVARIANTS
----------
* Never calls any GraphManager mutation method.
* Writes ONLY to cognition.topic_snapshots (idempotent ON CONFLICT DO NOTHING).
* Logs every run to cognition.compiler_runs (non-fatal on error).
* Never modifies graph.nodes or graph.edges.
"""

from __future__ import annotations

import json
import time
from typing import Optional, Dict, Any

from nexus.projection.document_compiler import DocumentCompiler, _document_to_dict
from nexus.projection.document_schema import StructuredDocument


# ---------------------------------------------------------------------------
# Version arithmetic
# ---------------------------------------------------------------------------

def _parse_version(version_str: str) -> tuple:
    """Parse 'major.minor.patch' → (major, minor, patch) ints."""
    try:
        parts = version_str.split(".")
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    except Exception:
        return (1, 0, 0)


def _bump_version(
    prev_section_count: int,
    new_section_count: int,
    current_version: str,
) -> tuple:
    """
    Compute next version and bump type.

    Returns
    -------
    (new_version_str, bump_type) where bump_type ∈ {'patch', 'minor', 'major'}
    """
    major, minor, patch = _parse_version(current_version)
    delta = abs(new_section_count - prev_section_count)

    if delta == 0:
        return (f"{major}.{minor}.{patch + 1}", "patch")
    elif delta <= 3:
        return (f"{major}.{minor + 1}.0", "minor")
    else:
        return (f"{major + 1}.0.0", "major")


# ---------------------------------------------------------------------------
# SnapshotService
# ---------------------------------------------------------------------------

class SnapshotService:
    """
    Deterministic versioning service for topic documents.

    Parameters
    ----------
    db :
        PostgresAdapter.  Injected for testability.
    """

    def __init__(self, db=None):
        if db is None:
            from nexus.db import get_adapter
            db = get_adapter()
        self.db = db
        self._compiler = DocumentCompiler(db=db, persist_snapshots=True)

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def snapshot_topic(self, topic_id: str) -> StructuredDocument:
        """
        Compile a topic and persist a new snapshot if the content has changed.

        If the hash matches the latest snapshot, the existing version is
        returned without a write (idempotent).

        Parameters
        ----------
        topic_id :
            The graph.nodes ID of the topic node.

        Returns
        -------
        StructuredDocument with the correct semver attached.
        """
        t0 = time.time()
        bump_type: Optional[str] = None
        doc: Optional[StructuredDocument] = None
        snapshot_saved = False

        try:
            # 1. Compile (READ-ONLY)
            doc = self._compiler.compile_topic(topic_id)

            # 2. Fetch last snapshot
            last = self._get_latest_snapshot_meta(topic_id)
            prev_hash = last["document_hash"] if last else None
            prev_sections = last["section_count"] if last else 0
            current_version = last["version"] if last else "0.0.0"

            # 3. Identical hash → skip write
            if prev_hash == doc.hash:
                doc.version = current_version
                return doc

            # 4. Compute next version
            if prev_hash is None:
                new_version = "1.0.0"
                bump_type = None
            else:
                new_version, bump_type = _bump_version(
                    prev_section_count=prev_sections,
                    new_section_count=len(doc.sections),
                    current_version=current_version,
                )

            doc.version = new_version

            # 5. Persist
            self._insert_snapshot(
                topic_id=topic_id,
                version=new_version,
                document_hash=doc.hash,
                doc=doc,
            )
            snapshot_saved = True

            return doc

        finally:
            duration_ms = int((time.time() - t0) * 1000)
            self._log_run(
                topic_id=topic_id,
                document_hash=doc.hash if doc else None,
                snapshot_saved=snapshot_saved,
                version_bumped=bump_type,
                duration_ms=duration_ms,
                error=None,
            )

    def get_latest_snapshot(self, topic_id: str) -> Optional[Dict[str, Any]]:
        """
        Return the latest persisted snapshot dict, or None.

        Does NOT recompile.  Read-only access to cognition.topic_snapshots.
        """
        row = self.db.fetch_one(
            """
            SELECT document_json, version, document_hash, created_at, section_count
            FROM cognition.topic_snapshots
            WHERE topic_id = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (topic_id,),
        )
        if not row:
            return None
        doc_json = row[0] if isinstance(row[0], dict) else json.loads(row[0])
        return {
            "document": doc_json,
            "version": row[1],
            "hash": row[2],
            "created_at": str(row[3]),
            "section_count": row[4],
        }

    def list_snapshots(self, topic_id: str, limit: int = 20) -> list:
        """
        List snapshot history for a topic, newest first.

        Returns a list of metadata dicts (does NOT include full document_json).
        """
        rows = self.db.fetch_all(
            """
            SELECT version, document_hash, section_count, created_at
            FROM cognition.topic_snapshots
            WHERE topic_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (topic_id, limit),
        )
        return [
            {
                "version": r[0],
                "hash": r[1],
                "section_count": r[2],
                "created_at": str(r[3]),
            }
            for r in rows
        ]

    def get_snapshot_by_version(
        self, topic_id: str, version: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific snapshot by semantic version.
        """
        row = self.db.fetch_one(
            """
            SELECT document_json, version, document_hash, created_at, section_count
            FROM cognition.topic_snapshots
            WHERE topic_id = %s AND version = %s
            LIMIT 1
            """,
            (topic_id, version),
        )
        if not row:
            return None
        doc_json = row[0] if isinstance(row[0], dict) else json.loads(row[0])
        return {
            "document": doc_json,
            "version": row[1],
            "hash": row[2],
            "created_at": str(row[3]),
            "section_count": row[4],
        }

    # ------------------------------------------------------------------
    # PRIVATE HELPERS
    # ------------------------------------------------------------------

    def _get_latest_snapshot_meta(self, topic_id: str) -> Optional[Dict]:
        """Fetch lightweight metadata from the most recent snapshot."""
        row = self.db.fetch_one(
            """
            SELECT version, document_hash, section_count
            FROM cognition.topic_snapshots
            WHERE topic_id = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (topic_id,),
        )
        if not row:
            return None
        return {
            "version": row[0],
            "document_hash": row[1],
            "section_count": row[2] or 0,
        }

    def _insert_snapshot(
        self,
        topic_id: str,
        version: str,
        document_hash: str,
        doc: StructuredDocument,
    ):
        """
        Persist a snapshot row.  Idempotent via ON CONFLICT DO NOTHING.
        A collision on (topic_id, version) means the same version was already
        persisted — that is fine; we skip silently.
        """
        doc_dict = _document_to_dict(doc)
        self.db.execute(
            """
            INSERT INTO cognition.topic_snapshots
                (topic_id, version, document_hash, document_json, section_count, intent_count)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (topic_id, version) DO NOTHING
            """,
            (
                topic_id,
                version,
                document_hash,
                json.dumps(doc_dict),
                len(doc.sections),
                len(doc.sections),
            ),
        )

    def _log_run(
        self,
        topic_id: str,
        document_hash: Optional[str],
        snapshot_saved: bool,
        version_bumped: Optional[str],
        duration_ms: int,
        error: Optional[str],
    ):
        """Non-fatal run logger."""
        try:
            self.db.execute(
                """
                INSERT INTO cognition.compiler_runs
                    (topic_id, document_hash, snapshot_saved, version_bumped, duration_ms, error)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (topic_id, document_hash, snapshot_saved, version_bumped, duration_ms, error),
            )
        except Exception as log_err:
            print(f"[SnapshotService] _log_run failed (non-fatal): {log_err}")
