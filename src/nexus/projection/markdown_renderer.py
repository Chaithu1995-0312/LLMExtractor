"""
Markdown Renderer — Nexus Cognitive Operating System v1.0
==========================================================

Converts a StructuredDocument into clean, human-readable Markdown.

READ-ONLY.  This module has no write path and no external dependencies
beyond the document_schema types.

Usage
-----
    from nexus.projection.markdown_renderer import render_markdown
    from nexus.projection.document_compiler import DocumentCompiler

    compiler = DocumentCompiler()
    doc = compiler.compile_topic(topic_id)
    md_text = render_markdown(doc)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nexus.projection.document_schema import StructuredDocument


# Mapping of section_type → display label
_SECTION_TYPE_LABELS: dict = {
    "definition":      "📖 Definition",
    "concept":         "💡 Concept",
    "mechanism":       "⚙️ Mechanism",
    "decision":        "🔀 Decision",
    "dependency":      "🔗 Dependency",
    "historical_note": "📜 Historical Note",
    "open_question":   "❓ Open Question",
}

_LIFECYCLE_BADGE: dict = {
    "frozen":  "🔒 frozen",
    "forming": "🔄 forming",
}


def render_markdown(doc: "StructuredDocument") -> str:
    """
    Render a StructuredDocument as a Markdown string.

    The output is deterministic: identical document state produces
    identical Markdown output.

    Parameters
    ----------
    doc :
        A StructuredDocument produced by DocumentCompiler.

    Returns
    -------
    str
        UTF-8 compatible Markdown string.
    """
    lines: list = []

    # ── Document header ────────────────────────────────────────────────
    lines.append(f"# {doc.topic_title}")
    lines.append("")
    lines.append(
        f"> **Version:** `{doc.version}`  "
        f"**Hash:** `{doc.hash[:16]}…`  "
        f"**Generated:** {doc.generated_at}"
    )
    lines.append("")

    section_count = len(doc.sections)
    if section_count == 0:
        lines.append("*No active sections found for this topic.*")
        lines.append("")
    else:
        lines.append(
            f"*{section_count} section{'s' if section_count != 1 else ''} — "
            f"superseded and killed nodes excluded.*"
        )
        lines.append("")

    # ── Table of contents ──────────────────────────────────────────────
    if doc.sections:
        lines.append("## Table of Contents")
        lines.append("")
        for i, section in enumerate(doc.sections, start=1):
            anchor = _make_anchor(section.title)
            label = _SECTION_TYPE_LABELS.get(section.section_type, section.section_type)
            lines.append(f"{i}. [{section.title}](#{anchor}) — {label}")
        lines.append("")
        lines.append("---")
        lines.append("")

    # ── Sections ───────────────────────────────────────────────────────
    for section in doc.sections:
        type_label = _SECTION_TYPE_LABELS.get(section.section_type, section.section_type)
        lifecycle_badge = _LIFECYCLE_BADGE.get(section.lifecycle, section.lifecycle)

        lines.append(f"## {section.title}")
        lines.append("")
        lines.append(
            f"*{type_label} · {lifecycle_badge} · "
            f"node `{section.node_id[:12]}…`*"
        )
        lines.append("")
        lines.append(section.content)
        lines.append("")

        if section.supersedes:
            plural = "s" if len(section.supersedes) > 1 else ""
            node_list = ", ".join(f"`{n[:12]}…`" for n in section.supersedes)
            lines.append(f"> *Supersedes node{plural}: {node_list}*")
            lines.append("")

        if section.metadata:
            # Only surface non-empty, non-trivial metadata keys
            useful_keys = {
                k: v for k, v in section.metadata.items()
                if v and k not in ("sync_topic_id", "sync_topic_name")
            }
            if useful_keys:
                lines.append("<details><summary>Metadata</summary>")
                lines.append("")
                for k, v in sorted(useful_keys.items()):
                    lines.append(f"- **{k}**: {v}")
                lines.append("")
                lines.append("</details>")
                lines.append("")

    # ── Cross-topic links ──────────────────────────────────────────────
    if doc.cross_topic_links:
        lines.append("---")
        lines.append("")
        lines.append("## Cross-Topic References")
        lines.append("")
        lines.append(
            "The following nodes in this topic reference knowledge from other topics:"
        )
        lines.append("")

        # Group by target topic for readability
        by_topic: dict = {}
        for link in doc.cross_topic_links:
            by_topic.setdefault(link.target_topic_id, []).append(link)

        for target_topic_id, links in sorted(by_topic.items()):
            lines.append(f"### → Topic `{target_topic_id}`")
            lines.append("")
            for link in links:
                lines.append(
                    f"- Node `{link.source_node_id[:12]}…` "
                    f"→ `{link.relationship}` "
                    f"→ node `{link.target_node_id[:12]}…`"
                )
            lines.append("")

    # ── Footer ─────────────────────────────────────────────────────────
    lines.append("---")
    lines.append("")
    lines.append(
        f"*Generated by Nexus Cognitive OS · DocumentCompiler v1.0 · "
        f"Topic: `{doc.topic_id}`*"
    )
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _make_anchor(title: str) -> str:
    """
    Convert a section title to a GitHub-flavoured Markdown anchor slug.
    Lowercases, replaces spaces with hyphens, strips non-alphanumeric characters.
    """
    slug = title.lower().strip()
    # Replace non-alphanumeric / non-hyphen chars with hyphen
    import re
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug
