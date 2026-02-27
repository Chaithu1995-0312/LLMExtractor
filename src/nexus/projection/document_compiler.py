"""
Deterministic Document Compiler — Nexus Cognitive Operating System v1.0
========================================================================

PURPOSE
-------
Convert a Topic graph into a structured, deterministic JSON document.
READ-ONLY — this module never calls GraphManager mutation methods.

DETERMINISM CONTRACT
--------------------
Given the same graph state, compile_topic() MUST return the same SHA-256
hash.  This is achieved by:
  1. Fetching only ACTIVE (forming) + FROZEN intents.
  2. Removing SUPERSEDED + KILLED nodes.
  3. Ordering sections by created_at ASC (stable, server-side).
  4. Serialising JSON with sorted keys.
  5. Computing SHA-256 of the UTF-8 encoded JSON string.

SECTION TYPES (spec §5.6)
--------------------------
  definition | concept | mechanism | decision |
  dependency | historical_note | open_question
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Data-classes
# ---------------------------------------------------------------------------

@dataclass
class CrossLink:
    """Reference from this topic's section to a node in another topic."""
    source_node_id: str
    target_topic_id: str
    target_node_id: str
    relationship: str          # edge_type string


@dataclass
class Section:
    """A compiled section representing one intent/concept node."""
    node_id: str
    section_type: str          # one of the 7 section types
    title: str
    content: str
    lifecycle: str
    created_at: str
    supersedes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StructuredDocument:
    topic_id: str
    topic_title: str
    version: str
    hash: str
    generated_at: str          # ISO-8601 UTC
    sections: List[Section]
    cross_topic_links: List[CrossLink]
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Section type inference
# ---------------------------------------------------------------------------

_SECTION_TYPE_KEYWORDS: Dict[str, List[str]] = {
    "definition":      ["definition", "define", "is defined as", "refers to", "meaning"],
    "mechanism":       ["mechanism", "process", "how it works", "algorithm", "flow", "pipeline"],
    "decision":        ["decision", "chose", "decided", "rationale", "trade-off", "we selected"],
    "dependency":      ["depends on", "requires", "dependency", "prerequisite", "relies on"],
    "historical_note": ["historically", "originally", "previous version", "deprecated", "legacy"],
    "open_question":   ["unclear", "open question", "tbd", "to be determined", "unknown"],
}


def _infer_section_type(statement: str, intent_type: str) -> str:
    """
    Heuristic section-type inference from node text + intent_type.
    Falls back to 'concept'.
    """
    lower = (statement or "").lower()
    for stype, keywords in _SECTION_TYPE_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return stype
    # Map well-known intent_type strings to section types
    _INTENT_MAP = {
        "definition": "definition",
        "mechanism":  "mechanism",
        "decision":   "decision",
        "dependency": "dependency",
        "question":   "open_question",
    }
    return _INTENT_MAP.get((intent_type or "").lower(), "concept")


# ---------------------------------------------------------------------------
# Version bump logic (spec §6.2)
# ---------------------------------------------------------------------------

def _compute_version_bump(
    prev_hash: Optional[str],
    prev_section_count: int,
    new_section_count: int,
    current_version: str,
) -> tuple[str, str]:
    """
    Returns (new_version, bump_type) where bump_type in
    {'patch', 'minor', 'major', None}.
    """
    if prev_hash is None:
        return "1.0.0", None  # First version

    try:
        major, minor, patch = (int(x) for x in current_version.split("."))
    except Exception:
        major, minor, patch = 1, 0, 0

    delta = new_section_count - prev_section_count

    if delta == 0:
        # No structural change at all → patch
        patch += 1
        return f"{major}.{minor}.{patch}", "patch"
    elif abs(delta) <= 3:
        # Small node addition or removal → minor
        minor += 1
        patch = 0
        return f"{major}.{minor}.{patch}", "minor"
    else:
        # Large structural reorder / many new concepts → major
        major += 1
        minor = 0
        patch = 0
        return f"{major}.{minor}.{patch}", "major"


# ---------------------------------------------------------------------------
# DocumentCompiler
# ---------------------------------------------------------------------------

class DocumentCompiler:
    """
    Read-only compiler.  Converts a topic's graph state into a
    StructuredDocument with a deterministic SHA-256 hash.

    Parameters
    ----------
    db :
        PostgresAdapter.  Injected for testability.
    persist_snapshots : bool
        When True, successful compilations are saved to
        cognition.topic_snapshots and cognition.compiler_runs.
    """

    def __init__(self, db=None, persist_snapshots: bool = True):
        if db is None:
            from nexus.db import get_adapter
            db = get_adapter()
        self.db = db
        self.persist_snapshots = persist_snapshots

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def compile_topic(self, topic_id: str) -> StructuredDocument:
        """
        Compile *topic_id* into a StructuredDocument.

        READ-ONLY.  Never calls any GraphManager mutation method.

        Raises
        ------
        ValueError
            If the topic node is not found.
        """
        t0 = time.time()
        error_msg: Optional[str] = None
        doc: Optional[StructuredDocument] = None

        try:
            doc = self._compile(topic_id)
        except Exception as e:
            error_msg = str(e)
            raise
        finally:
            duration_ms = int((time.time() - t0) * 1000)
            if self.persist_snapshots:
                self._log_run(
                    topic_id=topic_id,
                    document_hash=doc.hash if doc else None,
                    snapshot_saved=False,
                    version_bumped=None,
                    duration_ms=duration_ms,
                    error=error_msg,
                )

        return doc

    def compile_and_snapshot(self, topic_id: str) -> StructuredDocument:
        """
        Compile and persist a snapshot to cognition.topic_snapshots.

        Returns the StructuredDocument.  Version is bumped relative to the
        last stored snapshot per the spec §6.2 rules.
        """
        t0 = time.time()
        bump_type: Optional[str] = None
        doc: Optional[StructuredDocument] = None
        snapshot_saved = False

        try:
            doc = self._compile(topic_id)

            # Fetch last snapshot for this topic
            last = self.db.fetch_one(
                """
                SELECT document_hash, version, section_count
                FROM cognition.topic_snapshots
                WHERE topic_id = %s
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (topic_id,),
            )
            prev_hash = last[0] if last else None
            prev_sections = last[2] if last else 0
            current_version = last[1] if last else "0.0.0"

            # Identical hash → skip duplicate write
            if prev_hash == doc.hash:
                doc.version = current_version
                return doc

            new_version, bump_type = _compute_version_bump(
                prev_hash=prev_hash,
                prev_section_count=prev_sections,
                new_section_count=len(doc.sections),
                current_version=current_version,
            )
            doc.version = new_version

            # Persist snapshot
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
                    new_version,
                    doc.hash,
                    json.dumps(doc_dict),
                    len(doc.sections),
                    len(doc.sections),
                ),
            )
            snapshot_saved = True

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

        return doc

    def get_latest_snapshot(self, topic_id: str) -> Optional[Dict]:
        """
        Return the latest persisted snapshot dict, or None.
        """
        row = self.db.fetch_one(
            """
            SELECT document_json, version, document_hash, created_at
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
        }

    def render_markdown(self, doc: StructuredDocument) -> str:
        """
        Render a StructuredDocument to Markdown.
        """
        lines: List[str] = []
        lines.append(f"# {doc.topic_title}")
        lines.append(f"")
        lines.append(f"**Version:** {doc.version}  ")
        lines.append(f"**Hash:** `{doc.hash}`  ")
        lines.append(f"**Generated:** {doc.generated_at}")
        lines.append("")

        for section in doc.sections:
            lines.append(f"## {section.title}")
            lines.append(f"*Type: {section.section_type} | Lifecycle: {section.lifecycle}*")
            lines.append("")
            lines.append(section.content)
            lines.append("")
            if section.supersedes:
                lines.append(
                    f"> *Supersedes: {', '.join(section.supersedes)}*"
                )
                lines.append("")

        if doc.cross_topic_links:
            lines.append("---")
            lines.append("## Cross-Topic References")
            lines.append("")
            for link in doc.cross_topic_links:
                lines.append(
                    f"- [{link.target_topic_id}] node `{link.target_node_id}` "
                    f"via `{link.relationship}`"
                )
            lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # INTERNAL COMPILATION ENGINE
    # ------------------------------------------------------------------

    def _compile(self, topic_id: str) -> StructuredDocument:
        # ── 1. Fetch topic node ─────────────────────────────────────────
        topic_row = self.db.fetch_one(
            "SELECT data FROM graph.nodes WHERE id = %s AND type = 'topic'",
            (topic_id,),
        )
        if not topic_row:
            raise ValueError(f"Topic node not found: {topic_id}")
        topic_data = topic_row[0] if isinstance(topic_row[0], dict) else json.loads(topic_row[0])
        topic_title = (
            topic_data.get("name")
            or topic_data.get("title")
            or topic_data.get("statement")
            or topic_id
        )

        # ── 2. Fetch ACTIVE + FROZEN intents for this topic ─────────────
        rows = self.db.fetch_all(
            """
            SELECT n.id, n.data, n.created_at
            FROM graph.nodes n
            JOIN graph.edges e
                ON n.id = e.target_id
                AND e.source_id = %s
            WHERE n.type IN ('intent', 'concept', 'brick')
              AND (n.data->>'lifecycle') IN ('frozen', 'forming')
            ORDER BY n.created_at ASC
            """,
            (topic_id,),
        )

        # ── 3. Resolve supersession chains — remove SUPERSEDED / KILLED ──
        # Build superseded_by map from edges
        all_node_ids = [r[0] for r in rows]
        superseded_ids = set()
        if all_node_ids:
            sup_rows = self.db.fetch_all(
                """
                SELECT source_id, target_id
                FROM graph.edges
                WHERE source_id = ANY(%s)
                  AND edge_type = 'SUPERSEDED_BY'
                """,
                (all_node_ids,),
            )
            # Any node that has a SUPERSEDED_BY edge is no longer current
            superseded_ids = {r[0] for r in sup_rows}

        # Map old → new for supersedes metadata
        supersedes_map: Dict[str, List[str]] = {}
        for r in (self.db.fetch_all(
            """
            SELECT target_id, source_id
            FROM graph.edges
            WHERE target_id = ANY(%s)
              AND edge_type = 'SUPERSEDED_BY'
            """,
            (all_node_ids,),
        ) if all_node_ids else []):
            supersedes_map.setdefault(r[0], []).append(r[1])

        # ── 4. Build section tree ────────────────────────────────────────
        sections: List[Section] = []
        for row in rows:
            node_id = row[0]
            if node_id in superseded_ids:
                continue  # Skip superseded nodes

            data = row[1] if isinstance(row[1], dict) else json.loads(row[1] or "{}")
            lifecycle = data.get("lifecycle", "loose")

            # Double-check — exclude killed/superseded from data field too
            if lifecycle in ("superseded", "killed"):
                continue

            statement = (
                data.get("statement")
                or data.get("content")
                or data.get("name")
                or ""
            )
            intent_type = data.get("intent_type", "")
            section_type = _infer_section_type(statement, intent_type)

            # Title = first sentence, capped at 80 chars
            title = (statement.split(".")[0] or statement)[:80].strip()

            created_at = str(row[2]) if row[2] else ""

            sections.append(
                Section(
                    node_id=node_id,
                    section_type=section_type,
                    title=title,
                    content=statement,
                    lifecycle=lifecycle,
                    created_at=created_at,
                    supersedes=supersedes_map.get(node_id, []),
                    metadata=data.get("metadata", {}),
                )
            )

        # ── 5. Resolve cross-topic references ────────────────────────────
        cross_links: List[CrossLink] = []
        if all_node_ids:
            xref_rows = self.db.fetch_all(
                """
                SELECT e.source_id, e.target_id, e.edge_type,
                       n.data->>'sync_topic_id' AS target_topic
                FROM graph.edges e
                JOIN graph.nodes n ON n.id = e.target_id
                WHERE e.source_id = ANY(%s)
                  AND n.data->>'sync_topic_id' IS NOT NULL
                  AND n.data->>'sync_topic_id' != %s
                """,
                (all_node_ids, topic_id),
            )
            for xr in xref_rows:
                cross_links.append(CrossLink(
                    source_node_id=xr[0],
                    target_topic_id=xr[3] or "",
                    target_node_id=xr[1],
                    relationship=xr[2],
                ))

        # ── 6. Deterministic ordering — already done by ORDER BY created_at ASC

        # ── 7. Generate canonical JSON and compute SHA-256 hash ──────────
        # Ensure deep sorting of list fields for stable hashing
        doc_payload = {
            "topic_id": topic_id,
            "topic_title": topic_title,
            "sections": sorted([asdict(s) for s in sections], key=lambda x: x["created_at"]),
            "cross_topic_links": sorted([asdict(c) for c in cross_links], key=lambda x: (x["source_node_id"], x["target_node_id"])),
        }
        canonical_json = json.dumps(doc_payload, sort_keys=True, ensure_ascii=False)
        sha256 = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

        return StructuredDocument(
            topic_id=topic_id,
            topic_title=topic_title,
            version="1.0.0",     # caller may override on snapshot
            hash=sha256,
            generated_at=datetime.now(timezone.utc).isoformat(),
            sections=sections,
            cross_topic_links=cross_links,
            metadata={
                "section_count": len(sections),
                "cross_link_count": len(cross_links),
                "superseded_removed": len(superseded_ids),
            },
        )

    # ------------------------------------------------------------------
    # PERSISTENCE HELPERS
    # ------------------------------------------------------------------

    def _log_run(
        self,
        topic_id: str,
        document_hash: Optional[str],
        snapshot_saved: bool,
        version_bumped: Optional[str],
        duration_ms: int,
        error: Optional[str],
    ):
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
            # Non-fatal
            print(f"[DocumentCompiler] Failed to log run: {log_err}")


# ---------------------------------------------------------------------------
# Serialisation utility
# ---------------------------------------------------------------------------

def _document_to_dict(doc: StructuredDocument) -> Dict:
    """Convert StructuredDocument to a plain dict suitable for JSON storage."""
    d = asdict(doc)
    return d
