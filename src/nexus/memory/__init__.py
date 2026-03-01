"""
nexus.memory
============
Fully local semantic memory engine for Nexus.

Responsibilities:
- Ingest ChatGPT export JSON into deterministic, versioned datasets
- Chunk text with deterministic SHA256 chunk IDs
- Embed chunks via Ollama nomic-embed-text
- Persist vectors in a ChromaDB collection isolated from Graph vectors
- Support top-k semantic retrieval without forcing generation
- Support optional LLM summarization via llama3:latest
- Support explicit promotion of retrieved chunks to Nexus Bricks

Invariants:
- MUST NOT share vector namespace with graph.nodes or sync.bricks
- MUST NOT modify GraphManager
- MUST NOT bypass Cortex routing for Brick promotion
- ALL mutations are idempotent and logged
"""

from nexus.memory.dataset_manager import DatasetManager, MemoryDataset
from nexus.memory.chunker import Chunker, Chunk
from nexus.memory.embedder import MemoryEmbedder
from nexus.memory.vector_store import MemoryVectorStore, ChromaMemoryVectorStore
from nexus.memory.metadata_store import MetadataStore
from nexus.memory.retriever import MemoryRetriever
from nexus.memory.memory_service import MemoryService

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
