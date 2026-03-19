"""nexus.memory package public API.

Uses lazy attribute loading to avoid circular-import side effects during module
initialization (notably when vector and memory layers import each other).
"""

from __future__ import annotations

from importlib import import_module

__all__ = [
    "DatasetManager",
    "MemoryDataset",
    "Chunker",
    "Chunk",
    "MemoryEmbedder",
    "MemoryVectorStore",
    "ChromaMemoryVectorStore",
    "MetadataStore",
    "MemoryRetriever",
    "MemoryService",
]


def __getattr__(name: str):
    if name in {"DatasetManager", "MemoryDataset"}:
        m = import_module("nexus.memory.dataset_manager")
        return getattr(m, name)
    if name in {"Chunker", "Chunk"}:
        m = import_module("nexus.memory.chunker")
        return getattr(m, name)
    if name in {"MemoryEmbedder"}:
        m = import_module("nexus.memory.embedder")
        return getattr(m, name)
    if name in {"MemoryVectorStore", "ChromaMemoryVectorStore"}:
        m = import_module("nexus.memory.vector_store")
        return getattr(m, name)
    if name in {"MetadataStore"}:
        m = import_module("nexus.memory.metadata_store")
        return getattr(m, name)
    if name in {"MemoryRetriever"}:
        m = import_module("nexus.memory.retriever")
        return getattr(m, name)
    if name in {"MemoryService"}:
        m = import_module("nexus.memory.memory_service")
        return getattr(m, name)
    raise AttributeError(f"module 'nexus.memory' has no attribute {name!r}")
