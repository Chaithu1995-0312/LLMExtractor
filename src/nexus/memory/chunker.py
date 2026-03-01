"""
nexus.memory.chunker
====================
Deterministic text chunker for ChatGPT export JSON.

Chunk IDs are SHA256 hashes of (conversation_id + message_id + chunk_index),
guaranteeing stable, reproducible IDs across re-ingestion runs. This is the
foundation of idempotent ingestion: a chunk that already exists in the vector
store can be skipped without re-embedding.

Chunking strategy:
  - Split text by whitespace tokens (word-level approximation).
  - Slide a window of `chunk_size` tokens with `overlap` token overlap.
  - Minimum chunk length of 10 tokens is enforced to discard trivial fragments.

ChatGPT export format handled:
  Top-level JSON is a list of conversation objects:
  [
    {
      "id": "<conversation_id>",
      "title": "...",
      "create_time": 1700000000.0,
      "mapping": {
        "<node_id>": {
          "message": {
            "id": "<message_id>",
            "author": {"role": "user"|"assistant"|"system"},
            "create_time": 1700000001.0,
            "content": {"content_type": "text", "parts": ["..."]}
          }
        }
      }
    }
  ]
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import Iterator, List, Optional

logger = logging.getLogger(__name__)

# Defaults defined per specification.
DEFAULT_CHUNK_SIZE: int = 800   # tokens (word approximation)
DEFAULT_OVERLAP: int = 150      # tokens
MIN_CHUNK_TOKENS: int = 10      # discard trivially small trailing chunks


@dataclass
class Chunk:
    """A single text chunk produced by the Chunker."""

    chunk_id: str
    """Deterministic SHA256(conversation_id + message_id + str(chunk_index))."""

    text: str
    """Raw text content of this chunk."""

    conversation_id: str
    token_count: int
    chunk_index: int

    # Metadata for lineage tracking.
    message_id: str
    role: str
    timestamp: Optional[str]
    source: str = "chatgpt_export"
    dataset_id: str = ""


def _make_chunk_id(conversation_id: str, message_id: str, chunk_index: int) -> str:
    """
    Deterministic chunk ID.
    sha256(conversation_id || message_id || str(chunk_index))
    """
    raw = f"{conversation_id}{message_id}{chunk_index}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _tokenize(text: str) -> List[str]:
    """
    Lightweight whitespace tokenizer.
    Returns a list of non-empty tokens split on whitespace.
    No external library dependency — consistent across environments.
    """
    return text.split()


def _detokenize(tokens: List[str]) -> str:
    return " ".join(tokens)


def _extract_text_from_message(message: dict) -> Optional[str]:
    """
    Extract plain text from a ChatGPT message node.
    Handles both string 'parts' and the legacy plain-text content field.
    Returns None if no usable text is found.
    """
    if not message:
        return None

    content = message.get("content")
    if not content:
        return None

    # Modern format: {"content_type": "text", "parts": ["..."]}
    if isinstance(content, dict):
        parts = content.get("parts", [])
        text_parts = [p for p in parts if isinstance(p, str) and p.strip()]
        if text_parts:
            return " ".join(text_parts).strip()
        return None

    # Legacy format: content is a plain string.
    if isinstance(content, str) and content.strip():
        return content.strip()

    return None


class Chunker:
    """
    Chunks a ChatGPT export JSON into deterministic Chunk objects.

    Usage:
        chunker = Chunker(chunk_size=800, overlap=150)
        for chunk in chunker.chunk_export(export_data, dataset_id="abc"):
            ...

    The chunker is stateless and thread-safe. A new instance per ingestion
    job is recommended to isolate configuration.
    """

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        overlap: int = DEFAULT_OVERLAP,
    ):
        if overlap >= chunk_size:
            raise ValueError(
                f"overlap ({overlap}) must be less than chunk_size ({chunk_size})"
            )
        self.chunk_size = chunk_size
        self.overlap = overlap

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def chunk_export(
        self,
        export_data: list,
        dataset_id: str,
    ) -> Iterator[Chunk]:
        """
        Yield Chunk objects from a parsed ChatGPT export list.

        Args:
            export_data: Parsed JSON list from conversations.json.
            dataset_id:  The MemoryDataset UUID this ingestion belongs to.

        Yields:
            Chunk — one per sliding window over each message's text.
        """
        if not isinstance(export_data, list):
            raise ValueError("ChatGPT export must be a JSON array at top level.")

        for conversation in export_data:
            if not isinstance(conversation, dict):
                continue
            yield from self._chunk_conversation(conversation, dataset_id)

    def chunk_file(
        self,
        file_path: str,
        dataset_id: str,
    ) -> Iterator[Chunk]:
        """
        Stream-parse a ChatGPT export JSON file and yield Chunks.

        Uses ijson if available for memory-efficient streaming of large
        exports; falls back to json.load() for compatibility.
        """
        try:
            import ijson  # optional streaming parser

            with open(file_path, "r", encoding="utf-8") as fh:
                for conversation in ijson.items(fh, "item"):
                    yield from self._chunk_conversation(conversation, dataset_id)

        except ImportError:
            # Fallback: load full file. Fine for files < ~500 MB.
            logger.debug(
                "[Chunker] ijson not available — loading full file into memory."
            )
            with open(file_path, "r", encoding="utf-8") as fh:
                export_data = json.load(fh)
            yield from self.chunk_export(export_data, dataset_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _chunk_conversation(
        self,
        conversation: dict,
        dataset_id: str,
    ) -> Iterator[Chunk]:
        """Yield all chunks for a single conversation object."""
        conversation_id = conversation.get("id") or conversation.get("conversation_id", "")
        if not conversation_id:
            logger.warning("[Chunker] Skipping conversation with no id.")
            return

        # Support both 'mapping' (modern) and flat 'messages' list (legacy).
        mapping = conversation.get("mapping")
        if mapping and isinstance(mapping, dict):
            messages = self._extract_messages_from_mapping(mapping)
        else:
            messages = conversation.get("messages", [])

        for message in messages:
            if not isinstance(message, dict):
                continue
            yield from self._chunk_message(message, conversation_id, dataset_id)

    def _extract_messages_from_mapping(self, mapping: dict) -> List[dict]:
        """
        Flatten a ChatGPT mapping dict into an ordered list of message dicts.
        Walks the tree from root via 'children' links; falls back to
        values()-order if tree traversal is not possible.
        """
        # Build a parent->children map and find root nodes.
        nodes = {}
        for node_id, node in mapping.items():
            msg = node.get("message")
            parent = node.get("parent")
            children = node.get("children", [])
            nodes[node_id] = {
                "message": msg,
                "parent": parent,
                "children": children,
            }

        # Find roots (parent is None or not in mapping).
        roots = [nid for nid, n in nodes.items() if n["parent"] not in nodes]

        ordered: List[dict] = []
        visited = set()

        def dfs(node_id: str) -> None:
            if node_id in visited:
                return
            visited.add(node_id)
            node = nodes.get(node_id)
            if node and node["message"]:
                ordered.append(node["message"])
            for child_id in (node["children"] if node else []):
                dfs(child_id)

        for root_id in roots:
            dfs(root_id)

        # If DFS produced nothing, fall back to flat ordering.
        if not ordered:
            for node in mapping.values():
                msg = node.get("message")
                if msg:
                    ordered.append(msg)

        return ordered

    def _chunk_message(
        self,
        message: dict,
        conversation_id: str,
        dataset_id: str,
    ) -> Iterator[Chunk]:
        """
        Slide a window over the message text and yield Chunks.

        Skips system-role messages and messages with no extractable text.
        """
        author = message.get("author") or {}
        role = author.get("role", "unknown") if isinstance(author, dict) else "unknown"

        # Skip system turns — they are configuration, not memory.
        if role == "system":
            return

        message_id = message.get("id", "")
        if not message_id:
            return

        text = _extract_text_from_message(message)
        if not text:
            return

        # Timestamp: prefer create_time (epoch float), fallback to update_time.
        ts_raw = message.get("create_time") or message.get("update_time")
        timestamp: Optional[str] = None
        if ts_raw is not None:
            try:
                from datetime import datetime, timezone
                timestamp = datetime.fromtimestamp(float(ts_raw), tz=timezone.utc).isoformat()
            except Exception:
                timestamp = str(ts_raw)

        tokens = _tokenize(text)
        if len(tokens) < MIN_CHUNK_TOKENS:
            return

        chunk_index = 0
        start = 0

        while start < len(tokens):
            end = start + self.chunk_size
            window_tokens = tokens[start:end]

            if len(window_tokens) < MIN_CHUNK_TOKENS:
                break

            chunk_text = _detokenize(window_tokens)
            chunk_id = _make_chunk_id(conversation_id, message_id, chunk_index)

            yield Chunk(
                chunk_id=chunk_id,
                text=chunk_text,
                conversation_id=conversation_id,
                token_count=len(window_tokens),
                chunk_index=chunk_index,
                message_id=message_id,
                role=role,
                timestamp=timestamp,
                source="chatgpt_export",
                dataset_id=dataset_id,
            )

            chunk_index += 1
            # Advance start by (chunk_size - overlap) to create the sliding window.
            step = self.chunk_size - self.overlap
            start += step
