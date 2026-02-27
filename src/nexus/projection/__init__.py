# nexus.projection — Structured Knowledge Compiler projection layer
#
# Public API surface for the Semantic + Projection Layer.
# All imports are lazy to avoid circular dependencies at module load time.

from nexus.projection.document_schema import (
    StructuredDocument,
    Section,
    CrossLink,
    SECTION_TYPES,
)

from nexus.projection.document_compiler import (
    DocumentCompiler,
    _document_to_dict,
)

from nexus.projection.markdown_renderer import render_markdown

from nexus.projection.snapshot_service import SnapshotService

__all__ = [
    # Schema types
    "StructuredDocument",
    "Section",
    "CrossLink",
    "SECTION_TYPES",
    # Compiler
    "DocumentCompiler",
    "_document_to_dict",
    # Renderer
    "render_markdown",
    # Snapshot service
    "SnapshotService",
]
