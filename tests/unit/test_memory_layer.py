"""
tests/unit/test_memory_layer.py
================================
Unit tests for the Memory Layer subsystem.

Test coverage:
  1. Chunker — determinism, overlap, minimum size, ChatGPT format parsing
  2. Embedder — dimension validation, empty-text guard, retry logic stubs
  3. VectorStore — idempotent add, search, delete_by_dataset (in-memory Chroma)
  4. MetadataStore — save/get/delete on a temp SQLite DB
  5. Retriever — integration with mocked embedder + in-memory vector store
  6. DatasetManager — CRUD on temp SQLite DB
  7. MemoryService — ingest flow with mocked embedder
  8. GraphManager invariant check — memory layer DOES NOT touch graph tables

Isolation:
  - All tests that touch disk use pytest tmp_path fixtures.
  - ChromaDB is initialised with a temporary persist directory.
  - No network calls are made. Ollama calls are stubbed via monkeypatch.
  - GraphManager is NOT imported in memory module tests — its invariant
    test merely verifies the import isolation.
"""

import hashlib
import os
import sqlite3
import tempfile
import uuid
from typing import List
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_vector(dim: int = 768) -> List[float]:
    """Return a normalised fake vector of given dimension."""
    import math
    raw = [float(i % 13 + 1) for i in range(dim)]
    norm = math.sqrt(sum(x * x for x in raw))
    return [x / norm for x in raw]


def _minimal_export(n_conversations: int = 2, messages_per_conv: int = 2) -> list:
    """Build a minimal ChatGPT-format export list for testing."""
    conversations = []
    for ci in range(n_conversations):
        conv_id = f"conv_{ci}"
        mapping = {}
        prev_id = None
        for mi in range(messages_per_conv):
            node_id = f"node_{ci}_{mi}"
            msg_id = f"msg_{ci}_{mi}"
            role = "user" if mi % 2 == 0 else "assistant"
            text = (f"This is message {mi} in conversation {ci}. " * 20).strip()
            mapping[node_id] = {
                "id": node_id,
                "parent": prev_id,
                "children": [],
                "message": {
                    "id": msg_id,
                    "author": {"role": role},
                    "create_time": 1700000000.0 + ci * 100 + mi,
                    "content": {
                        "content_type": "text",
                        "parts": [text],
                    },
                },
            }
            # Link parent's children.
            if prev_id and prev_id in mapping:
                mapping[prev_id]["children"].append(node_id)
            prev_id = node_id
        conversations.append({"id": conv_id, "title": f"Conv {ci}", "mapping": mapping})
    return conversations


# ===========================================================================
# 1. CHUNKER TESTS
# ===========================================================================

class TestChunker:

    def test_chunk_id_is_deterministic(self):
        """Same (conversation_id, message_id, chunk_index) always produces same SHA256."""
        from nexus.memory.chunker import _make_chunk_id
        cid1 = _make_chunk_id("conv_A", "msg_1", 0)
        cid2 = _make_chunk_id("conv_A", "msg_1", 0)
        cid3 = _make_chunk_id("conv_A", "msg_1", 1)
        assert cid1 == cid2, "Chunk ID must be deterministic."
        assert cid1 != cid3, "Different chunk_index must produce different ID."

    def test_chunk_id_is_sha256_hex(self):
        """Chunk ID should be a 64-char hex string (SHA256)."""
        from nexus.memory.chunker import _make_chunk_id
        cid = _make_chunk_id("conv_x", "msg_y", 5)
        assert len(cid) == 64
        int(cid, 16)  # Should not raise — confirms it's valid hex.

    def test_chunk_id_matches_manual_sha256(self):
        from nexus.memory.chunker import _make_chunk_id
        raw = "conv_xmsg_y5"
        expected = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        assert _make_chunk_id("conv_x", "msg_y", 5) == expected

    def test_chunker_produces_chunks(self):
        """Chunker must produce at least one chunk per long message."""
        from nexus.memory.chunker import Chunker
        export = _minimal_export(n_conversations=1, messages_per_conv=1)
        chunker = Chunker(chunk_size=50, overlap=10)
        chunks = list(chunker.chunk_export(export, dataset_id="test-ds"))
        assert len(chunks) > 0, "Expected at least one chunk."

    def test_chunker_skips_system_role(self):
        """System-role messages must be excluded from chunks."""
        from nexus.memory.chunker import Chunker
        conv = {
            "id": "conv_sys",
            "mapping": {
                "n1": {
                    "id": "n1",
                    "parent": None,
                    "children": [],
                    "message": {
                        "id": "msg_sys",
                        "author": {"role": "system"},
                        "create_time": 1700000000.0,
                        "content": {"content_type": "text", "parts": ["SYSTEM PROMPT " * 20]},
                    },
                }
            },
        }
        chunker = Chunker()
        chunks = list(chunker.chunk_export([conv], dataset_id="ds"))
        roles = [c.role for c in chunks]
        assert "system" not in roles

    def test_chunker_overlap_produces_multiple_chunks(self):
        """A message longer than chunk_size must produce multiple overlapping chunks."""
        from nexus.memory.chunker import Chunker, _tokenize
        long_text = "word " * 300   # 300 tokens
        conv = {
            "id": "conv_long",
            "mapping": {
                "n1": {
                    "id": "n1",
                    "parent": None,
                    "children": [],
                    "message": {
                        "id": "msg_long",
                        "author": {"role": "user"},
                        "create_time": 1700000000.0,
                        "content": {"content_type": "text", "parts": [long_text]},
                    },
                }
            },
        }
        chunker = Chunker(chunk_size=100, overlap=20)
        chunks = list(chunker.chunk_export([conv], dataset_id="ds"))
        assert len(chunks) >= 3, f"Expected >=3 chunks for 300-token text, got {len(chunks)}"

    def test_chunker_all_chunk_ids_unique(self):
        """Every chunk produced from a multi-conversation export must have a unique ID."""
        from nexus.memory.chunker import Chunker
        export = _minimal_export(n_conversations=3, messages_per_conv=3)
        chunker = Chunker(chunk_size=50, overlap=10)
        chunks = list(chunker.chunk_export(export, dataset_id="ds"))
        ids = [c.chunk_id for c in chunks]
        assert len(ids) == len(set(ids)), "All chunk IDs must be unique."

    def test_chunker_raises_on_non_list(self):
        """Passing a dict instead of a list must raise ValueError."""
        from nexus.memory.chunker import Chunker
        chunker = Chunker()
        with pytest.raises(ValueError, match="JSON array"):
            list(chunker.chunk_export({"not": "a list"}, dataset_id="ds"))

    def test_chunker_overlap_must_be_less_than_chunk_size(self):
        from nexus.memory.chunker import Chunker
        with pytest.raises(ValueError):
            Chunker(chunk_size=100, overlap=100)

    def test_chunk_metadata_fields(self):
        """Each chunk must carry all required metadata fields."""
        from nexus.memory.chunker import Chunker
        export = _minimal_export(n_conversations=1, messages_per_conv=1)
        chunker = Chunker(chunk_size=50, overlap=10)
        chunk = next(chunker.chunk_export(export, dataset_id="my-dataset"))
        assert chunk.chunk_id
        assert chunk.conversation_id
        assert chunk.message_id
        assert chunk.role in ("user", "assistant")
        assert chunk.source == "chatgpt_export"
        assert chunk.dataset_id == "my-dataset"
        assert chunk.token_count > 0


# ===========================================================================
# 2. EMBEDDER TESTS
# ===========================================================================

class TestMemoryEmbedder:

    def test_empty_text_raises(self):
        from nexus.memory.embedder import MemoryEmbedder
        embedder = MemoryEmbedder()
        with pytest.raises(ValueError, match="empty"):
            embedder.embed("")

    def test_dimension_validation_passes_on_correct_dim(self):
        from nexus.memory.embedder import MemoryEmbedder, EXPECTED_DIMENSION
        embedder = MemoryEmbedder()
        # Inject a fake valid vector.
        vec = _make_fake_vector(EXPECTED_DIMENSION)
        # Should not raise.
        embedder._validate_dimension(vec)
        assert embedder.dimension == EXPECTED_DIMENSION

    def test_dimension_validation_raises_on_wrong_dim(self):
        from nexus.memory.embedder import MemoryEmbedder, EmbeddingDimensionError
        embedder = MemoryEmbedder()
        vec = _make_fake_vector(384)  # wrong dimension for nomic-embed-text
        with pytest.raises(EmbeddingDimensionError):
            embedder._validate_dimension(vec)

    def test_embed_calls_ollama_endpoint(self):
        """embed() must POST to the configured Ollama endpoint."""
        from nexus.memory.embedder import MemoryEmbedder, EXPECTED_DIMENSION
        fake_vec = _make_fake_vector(EXPECTED_DIMENSION)

        with patch("nexus.memory.embedder.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"embedding": fake_vec}
            mock_resp.raise_for_status = MagicMock()
            mock_post.return_value = mock_resp

            embedder = MemoryEmbedder()
            result = embedder.embed("hello world")

        assert len(result) == EXPECTED_DIMENSION
        mock_post.assert_called_once()

    def test_embed_retries_on_connection_error(self):
        """ConnectionError must trigger retries up to max_retries."""
        from nexus.memory.embedder import MemoryEmbedder, OllamaUnavailableError, EXPECTED_DIMENSION
        import requests as req_lib

        with patch("nexus.memory.embedder.requests.post") as mock_post:
            mock_post.side_effect = req_lib.exceptions.ConnectionError("refused")
            embedder = MemoryEmbedder(max_retries=2)
            # Patch sleep to speed up test.
            with patch("nexus.memory.embedder.time.sleep"):
                with pytest.raises(OllamaUnavailableError):
                    embedder.embed("hello")
        assert mock_post.call_count == 2

    def test_check_availability_returns_false_on_failure(self):
        from nexus.memory.embedder import MemoryEmbedder
        import requests as req_lib

        with patch("nexus.memory.embedder.requests.post") as mock_post:
            mock_post.side_effect = req_lib.exceptions.ConnectionError("refused")
            embedder = MemoryEmbedder()
            result = embedder.check_availability()
        assert result is False


# ===========================================================================
# 3. VECTOR STORE TESTS  (in-memory ChromaDB)
# ===========================================================================

class TestChromaMemoryVectorStore:

    @pytest.fixture
    def store(self, tmp_path):
        """Provide a ChromaMemoryVectorStore backed by a temp directory."""
        from nexus.memory.vector_store import ChromaMemoryVectorStore
        coll_name = f"test_{uuid.uuid4().hex[:8]}"
        return ChromaMemoryVectorStore(
            collection_name=coll_name,
            persist_dir=str(tmp_path / "chroma"),
        )

    def test_add_and_count(self, store):
        vec = _make_fake_vector(768)
        store.add("chunk_001", vec, {"dataset_id": "ds1", "role": "user"}, "Hello world")
        assert store.count() == 1

    def test_add_is_idempotent(self, store):
        vec = _make_fake_vector(768)
        store.add("chunk_001", vec, {"dataset_id": "ds1"}, "text")
        store.add("chunk_001", vec, {"dataset_id": "ds1"}, "text")  # second add
        assert store.count() == 1

    def test_exists(self, store):
        assert not store.exists("chunk_999")
        vec = _make_fake_vector(768)
        store.add("chunk_999", vec, {"dataset_id": "ds1"}, "text")
        assert store.exists("chunk_999")

    def test_search_returns_results(self, store):
        vec = _make_fake_vector(768)
        store.add("chunk_a", vec, {"dataset_id": "ds1", "role": "user"}, "machine learning")
        results = store.search(query_vector=vec, top_k=5)
        assert len(results) >= 1
        assert results[0]["chunk_id"] == "chunk_a"
        assert 0.0 <= results[0]["score"] <= 1.0

    def test_search_returns_empty_on_empty_store(self, store):
        vec = _make_fake_vector(768)
        results = store.search(query_vector=vec, top_k=5)
        assert results == []

    def test_delete_by_dataset(self, store):
        vec = _make_fake_vector(768)
        store.add("c1", vec, {"dataset_id": "ds_del"}, "text1")
        store.add("c2", vec, {"dataset_id": "ds_keep"}, "text2")
        deleted = store.delete_by_dataset("ds_del")
        assert deleted == 1
        assert store.count() == 1
        assert not store.exists("c1")
        assert store.exists("c2")

    def test_count_by_dataset(self, store):
        vec = _make_fake_vector(768)
        store.add("d1_c1", vec, {"dataset_id": "ds_x"}, "t1")
        store.add("d1_c2", vec, {"dataset_id": "ds_x"}, "t2")
        store.add("d2_c1", vec, {"dataset_id": "ds_y"}, "t3")
        assert store.count_by_dataset("ds_x") == 2
        assert store.count_by_dataset("ds_y") == 1


# ===========================================================================
# 4. METADATA STORE TESTS
# ===========================================================================

class TestMetadataStore:

    @pytest.fixture
    def store(self, tmp_path, monkeypatch):
        """MetadataStore backed by a temp SQLite file."""
        db_path = str(tmp_path / "memory_test.db")
        monkeypatch.setattr("nexus.memory._db.get_memory_db_path", lambda: db_path)
        from nexus.memory.metadata_store import MetadataStore
        return MetadataStore()

    def _make_chunk(self, chunk_id: str = None, dataset_id: str = "ds1") -> object:
        from nexus.memory.chunker import Chunk
        return Chunk(
            chunk_id=chunk_id or hashlib.sha256(uuid.uuid4().hex.encode()).hexdigest(),
            text="This is a test chunk with enough words to be useful.",
            conversation_id="conv_001",
            token_count=12,
            chunk_index=0,
            message_id="msg_001",
            role="user",
            timestamp="2024-01-01T00:00:00+00:00",
            source="chatgpt_export",
            dataset_id=dataset_id,
        )

    def test_save_and_get_chunk(self, store):
        chunk = self._make_chunk()
        inserted = store.save_chunk(chunk)
        assert inserted is True
        row = store.get_chunk(chunk.chunk_id)
        assert row is not None
        assert row["text"] == chunk.text
        assert row["role"] == "user"

    def test_save_chunk_idempotent(self, store):
        chunk = self._make_chunk()
        store.save_chunk(chunk)
        inserted_again = store.save_chunk(chunk)
        assert inserted_again is False  # Already exists.

    def test_exists(self, store):
        chunk = self._make_chunk()
        assert not store.exists(chunk.chunk_id)
        store.save_chunk(chunk)
        assert store.exists(chunk.chunk_id)

    def test_delete_by_dataset(self, store):
        c1 = self._make_chunk(dataset_id="ds_del")
        c2 = self._make_chunk(dataset_id="ds_keep")
        store.save_chunk(c1)
        store.save_chunk(c2)
        deleted = store.delete_by_dataset("ds_del")
        assert deleted == 1
        assert store.get_chunk(c1.chunk_id) is None
        assert store.get_chunk(c2.chunk_id) is not None

    def test_count_by_dataset(self, store):
        for _ in range(3):
            store.save_chunk(self._make_chunk(dataset_id="ds_count"))
        assert store.count_by_dataset("ds_count") == 3

    def test_get_chunks_by_ids(self, store):
        chunks = [self._make_chunk() for _ in range(4)]
        for c in chunks:
            store.save_chunk(c)
        ids = [c.chunk_id for c in chunks[:2]]
        result = store.get_chunks_by_ids(ids)
        assert len(result) == 2
        for cid in ids:
            assert cid in result

    def test_save_batch(self, store):
        chunks = [self._make_chunk() for _ in range(10)]
        store.save_chunks_batch(chunks)
        assert store.total_count() == 10


# ===========================================================================
# 5. DATASET MANAGER TESTS
# ===========================================================================

class TestDatasetManager:

    @pytest.fixture
    def manager(self, tmp_path, monkeypatch):
        db_path = str(tmp_path / "dm_test.db")
        monkeypatch.setattr("nexus.memory._db.get_memory_db_path", lambda: db_path)
        from nexus.memory.dataset_manager import DatasetManager
        return DatasetManager()

    def test_create_dataset(self, manager):
        ds = manager.create_dataset("export.json")
        assert ds.dataset_id
        assert ds.dataset_version == 1
        assert ds.status == "PENDING"
        assert ds.source_filename == "export.json"

    def test_version_increments_on_same_source(self, manager):
        ds1 = manager.create_dataset("export.json")
        ds2 = manager.create_dataset("export.json")
        assert ds2.dataset_version == ds1.dataset_version + 1

    def test_get_dataset(self, manager):
        ds = manager.create_dataset("x.json")
        fetched = manager.get_dataset(ds.dataset_id)
        assert fetched is not None
        assert fetched.dataset_id == ds.dataset_id

    def test_get_dataset_returns_none_for_unknown(self, manager):
        assert manager.get_dataset("nonexistent-id") is None

    def test_update_status(self, manager):
        ds = manager.create_dataset("y.json")
        manager.update_status(ds.dataset_id, status="RUNNING")
        updated = manager.get_dataset(ds.dataset_id)
        assert updated.status == "RUNNING"

    def test_update_status_with_counts(self, manager):
        ds = manager.create_dataset("z.json")
        manager.update_status(ds.dataset_id, status="COMPLETE", total_chunks=42, total_conversations=5)
        updated = manager.get_dataset(ds.dataset_id)
        assert updated.total_chunks == 42
        assert updated.total_conversations == 5

    def test_list_datasets(self, manager):
        manager.create_dataset("a.json")
        manager.create_dataset("b.json")
        all_ds = manager.list_datasets()
        assert len(all_ds) == 2

    def test_clear_dataset(self, manager):
        ds = manager.create_dataset("c.json")
        manager.clear_dataset(ds.dataset_id)
        updated = manager.get_dataset(ds.dataset_id)
        assert updated.status == "CLEARED"


# ===========================================================================
# 6. RETRIEVER TESTS (mocked embedder + in-memory Chroma)
# ===========================================================================

class TestMemoryRetriever:

    @pytest.fixture
    def retriever(self, tmp_path, monkeypatch):
        db_path = str(tmp_path / "ret_test.db")
        monkeypatch.setattr("nexus.memory._db.get_memory_db_path", lambda: db_path)

        from nexus.memory.embedder import MemoryEmbedder, EXPECTED_DIMENSION
        from nexus.memory.metadata_store import MetadataStore
        from nexus.memory.retriever import MemoryRetriever
        from nexus.memory.vector_store import ChromaMemoryVectorStore

        fake_vec = _make_fake_vector(EXPECTED_DIMENSION)
        mock_embedder = MagicMock(spec=MemoryEmbedder)
        mock_embedder.embed.return_value = fake_vec
        mock_embedder.model = "nomic-embed-text"

        vs = ChromaMemoryVectorStore(
            collection_name=f"ret_{uuid.uuid4().hex[:8]}",
            persist_dir=str(tmp_path / "chroma"),
        )
        ms = MetadataStore()

        return MemoryRetriever(embedder=mock_embedder, vector_store=vs, metadata_store=ms)

    def test_empty_query_returns_empty(self, retriever):
        result = retriever.retrieve("", top_k=5)
        assert result.chunks == []
        assert result.retrieval_metadata["error"] == "empty_query"

    def test_retrieve_returns_chunk_results(self, tmp_path, monkeypatch):
        db_path = str(tmp_path / "ret2.db")
        monkeypatch.setattr("nexus.memory._db.get_memory_db_path", lambda: db_path)

        from nexus.memory.chunker import Chunk
        from nexus.memory.embedder import MemoryEmbedder, EXPECTED_DIMENSION
        from nexus.memory.metadata_store import MetadataStore
        from nexus.memory.retriever import MemoryRetriever
        from nexus.memory.vector_store import ChromaMemoryVectorStore

        fake_vec = _make_fake_vector(EXPECTED_DIMENSION)
        mock_embedder = MagicMock(spec=MemoryEmbedder)
        mock_embedder.embed.return_value = fake_vec
        mock_embedder.model = "nomic-embed-text"

        vs = ChromaMemoryVectorStore(
            collection_name=f"ret2_{uuid.uuid4().hex[:8]}",
            persist_dir=str(tmp_path / "chroma2"),
        )
        ms = MetadataStore()

        chunk = Chunk(
            chunk_id="abc123",
            text="Python async programming patterns",
            conversation_id="conv_1",
            token_count=5,
            chunk_index=0,
            message_id="msg_1",
            role="user",
            timestamp=None,
            source="chatgpt_export",
            dataset_id="ds_test",
        )
        ms.save_chunk(chunk)
        vs.add("abc123", fake_vec, {"dataset_id": "ds_test", "role": "user"}, chunk.text)

        retriever = MemoryRetriever(embedder=mock_embedder, vector_store=vs, metadata_store=ms)
        result = retriever.retrieve("async Python", top_k=5)

        assert len(result.chunks) == 1
        assert result.chunks[0].chunk_id == "abc123"
        assert result.chunks[0].score >= 0.0
        assert result.retrieval_metadata["returned_chunks"] == 1

    def test_retrieval_metadata_fields(self, retriever):
        result = retriever.retrieve("test query", top_k=3)
        meta = result.retrieval_metadata
        assert "model_used" in meta
        assert "index_size" in meta
        assert "mean_score" in meta
        assert "top_score" in meta
        assert "timestamp" in meta


# ===========================================================================
# 7. MEMORY SERVICE — INGEST FLOW (mocked Ollama)
# ===========================================================================

class TestMemoryServiceIngest:

    @pytest.fixture
    def service(self, tmp_path, monkeypatch):
        db_path = str(tmp_path / "svc_test.db")
        monkeypatch.setattr("nexus.memory._db.get_memory_db_path", lambda: db_path)

        from nexus.memory.embedder import EXPECTED_DIMENSION
        from nexus.memory.memory_service import MemoryService
        from nexus.memory.vector_store import ChromaMemoryVectorStore

        fake_vec = _make_fake_vector(EXPECTED_DIMENSION)

        vs = ChromaMemoryVectorStore(
            collection_name=f"svc_{uuid.uuid4().hex[:8]}",
            persist_dir=str(tmp_path / "chroma_svc"),
        )

        svc = MemoryService(chunk_size=50, overlap=10, vector_store=vs)
        # Stub the embedder so no real Ollama call is made.
        svc._embedder.embed = MagicMock(return_value=fake_vec)
        svc._retriever._embedder.embed = MagicMock(return_value=fake_vec)
        return svc

    def test_ingest_returns_complete_status(self, service):
        export = _minimal_export(n_conversations=2, messages_per_conv=2)
        result = service.ingest(export, source_filename="test_export.json")
        assert result["status"] == "COMPLETE"
        assert result["total_chunks"] > 0
        assert result["conversations"] == 2

    def test_ingest_is_idempotent(self, service):
        export = _minimal_export(n_conversations=1, messages_per_conv=1)
        r1 = service.ingest(export, source_filename="idempotent.json")
        r2 = service.ingest(export, source_filename="idempotent.json")
        # Second run should skip all chunks (they already exist).
        assert r2["skipped"] >= r1["total_chunks"]

    def test_ingest_empty_export(self, service):
        result = service.ingest([], source_filename="empty.json")
        assert result["total_chunks"] == 0
        assert result["status"] == "COMPLETE"

    def test_ingest_records_dataset(self, service):
        export = _minimal_export(n_conversations=1, messages_per_conv=1)
        result = service.ingest(export, source_filename="recorded.json")
        ds = service.get_dataset(result["dataset_id"])
        assert ds is not None
        assert ds["status"] == "COMPLETE"
        assert ds["total_chunks"] == result["total_chunks"]

    def test_retrieve_after_ingest(self, service):
        export = _minimal_export(n_conversations=1, messages_per_conv=2)
        service.ingest(export, source_filename="retrieve_test.json")
        result = service.retrieve("conversation messages", top_k=5)
        assert "chunks" in result
        assert "retrieval_metadata" in result

    def test_clear_dataset_removes_vectors_and_chunks(self, service):
        export = _minimal_export(n_conversations=1, messages_per_conv=1)
        ingest_result = service.ingest(export, source_filename="clear_test.json")
        dataset_id = ingest_result["dataset_id"]

        clear_result = service.clear_dataset(dataset_id)
        assert clear_result["status"] == "CLEARED"
        assert clear_result["chunks_deleted"] > 0

        ds = service.get_dataset(dataset_id)
        assert ds["status"] == "CLEARED"


# ===========================================================================
# 8. GRAPH MANAGER INVARIANT CHECK
# ===========================================================================

class TestMemoryLayerGraphIsolation:
    """
    These tests verify that the Memory Layer does NOT import or mutate
    GraphManager's FAISS index or graph.nodes table.
    """

    def test_memory_modules_do_not_import_graphmanager_at_module_level(self):
        """
        Memory Layer core modules must not import GraphManager at module
        load time. Only memory_service.promote_to_brick() imports it lazily.
        """
        import importlib
        import sys

        # Force reload to simulate fresh import.
        mods_to_check = [
            "nexus.memory._db",
            "nexus.memory.chunker",
            "nexus.memory.embedder",
            "nexus.memory.vector_store",
            "nexus.memory.metadata_store",
            "nexus.memory.retriever",
        ]
        for mod_name in mods_to_check:
            # Remove from sys.modules to test clean import.
            sys.modules.pop(mod_name, None)
            mod = importlib.import_module(mod_name)
            # GraphManager must NOT be in the module's namespace.
            assert not hasattr(mod, "GraphManager"), (
                f"{mod_name} must not import GraphManager at module level. "
                "Doing so would create a tight coupling and risk circular imports."
            )

    def test_memory_vector_store_uses_different_collection_than_graph(self):
        """
        ChromaDB collection name must differ from any graph vector namespace.
        The graph uses FAISS — not Chroma — so there's no direct collision,
        but we enforce the collection name to make the boundary explicit.
        """
        from nexus.memory.vector_store import MEMORY_COLLECTION_NAME
        # The graph uses FAISS (data/vector_index.faiss). It has no Chroma collection.
        # But if someone adds Chroma later, this name must remain distinct.
        assert MEMORY_COLLECTION_NAME == "memory_chat_exports"
        assert "graph" not in MEMORY_COLLECTION_NAME.lower()
        assert "node" not in MEMORY_COLLECTION_NAME.lower()
        assert "brick" not in MEMORY_COLLECTION_NAME.lower()

    def test_memory_db_path_is_not_graph_db_path(self):
        """
        The memory SQLite file must be different from the graph SQLite file.
        """
        from nexus.memory._db import get_memory_db_path
        from nexus.config import GRAPH_DB_PATH
        mem_path = get_memory_db_path()
        assert os.path.abspath(mem_path) != os.path.abspath(GRAPH_DB_PATH), (
            "Memory Layer DB must be a different file from Graph DB."
        )
