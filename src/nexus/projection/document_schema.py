"""
Document Schema — Nexus Cognitive Operating System v1.0
========================================================

Canonical data-classes for the Deterministic Document Compiler.

All types are pure data-classes with no external dependencies.
Importable by any layer without causing circular imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Primitive building blocks
# ---------------------------------------------------------------------------

@dataclass
class CrossLink:
    """
    Reference from one section in this document to a node in another topic.

    Attributes
    ----------
    source_node_id :
        The node in THIS topic that references another topic.
    target_topic_id :
        The remote topic ID being referenced.
    target_node_id :
        The specific node in the remote topic.
    relationship :
        Edge type string (e.g. 'DEPENDS_ON', 'RELATED_TO').
    """
    source_node_id: str
    target_topic_id: str
    target_node_id: str
    relationship: str


# ---------------------------------------------------------------------------
# Section — one logical unit of knowledge
# ---------------------------------------------------------------------------

# Allowed section types (spec §5.6)
SECTION_TYPES = frozenset({
    "definition",
    "concept",
    "mechanism",
    "decision",
    "dependency",
    "historical_note",
    "open_question",
})


@dataclass
class Section:
    """
    A compiled section representing one intent/concept/brick node.

    Lifecycle values that may appear here: 'forming', 'frozen'.
    Nodes with lifecycle 'superseded' or 'killed' are excluded by the compiler.

    Attributes
    ----------
    node_id :
        ID of the source graph node.
    section_type :
        One of the 7 canonical section types.
    title :
        First sentence of content, capped at 80 characters.
    content :
        Full statement / content text of the node.
    lifecycle :
        Current lifecycle state ('forming' or 'frozen').
    created_at :
        ISO-8601 string from graph.nodes.created_at.
    supersedes :
        List of node IDs that this section replaces.
    metadata :
        Arbitrary metadata dict from node data.
    """
    node_id: str
    section_type: str
    title: str
    content: str
    lifecycle: str
    created_at: str
    supersedes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# StructuredDocument — the compiled topic document
# ---------------------------------------------------------------------------

@dataclass
class StructuredDocument:
    """
    The final output of DocumentCompiler.compile_topic().

    Attributes
    ----------
    topic_id :
        graph.nodes ID of the source topic node.
    topic_title :
        Human-readable topic name.
    version :
        Semver string, e.g. "1.0.0".  Set by SnapshotService or compile_and_snapshot().
    hash :
        SHA-256 of the canonical JSON representation.
    generated_at :
        ISO-8601 UTC timestamp when the document was compiled.
    sections :
        Ordered list of Sections, sorted by created_at ASC.
    cross_topic_links :
        Outgoing cross-topic references.
    metadata :
        Compiler statistics (section_count, superseded_removed, etc.).
    """
    topic_id: str
    topic_title: str
    version: str
    hash: str
    generated_at: str
    sections: List[Section]
    cross_topic_links: List[CrossLink]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
