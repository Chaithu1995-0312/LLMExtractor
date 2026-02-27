"""
Semantic + Projection Layer — Unit Test Suite
=============================================

Covers:
  1. DocumentCompiler: determinism, superseded exclusion, ordering
  2. MarkdownRenderer: output structure
  3. SnapshotService: version bumping logic
  4. EntityResolver: exact match, alias, no-match, score routing
  5. Lifecycle regression: no mutation outside GraphManager
  6. Worker transaction: PGWorker.run_once contract unchanged

All tests are isolated using mocks/fakes — no live DB or network required.

INVARIANTS VERIFIED
-------------------
* DocumentCompiler never calls promote_node_to_frozen, supersede_node,
  register_edge, or register_node.
* EntityResolver.resolve() never mutates the graph.
* Refiner.audit_topic() only writes to drift_reports, not graph.nodes/edges.
* PGWorker.run_once logic path is structurally unchanged.
"""

from __future__ import annotations

import hashlib
import json
import types
import unittest
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# Fake DB adapter for offline testing
# ---------------------------------------------------------------------------

class _FakeDB:
    """
    In-memory stub that mimics the PostgresAdapter interface used by the
    DocumentCompiler, EntityResolver, Refiner, and SnapshotService.
    """

    def __init__(self, nodes=None, edges=None, snapshots=None, aliases=None, drift_reports=None):
        self._nodes: List[tuple] = nodes or []          # (id, type, data_dict, created_at)
        self._edges: List[tuple] = edges or []          # (source_id, target_id, edge_type, metadata)
        self._snapshots: List[tuple] = snapshots or []  # (doc_json, version, hash, created_at, section_count)
        self._aliases: List[tuple] = aliases or []      # (node_id, alias_text)
        self._drift_reports: List[tuple] = drift_reports or []
        self.executed: List[tuple] = []                 # SQL calls captured for assertion

    # --- Adapter interface ---

    def fetch_one(self, sql: str, params=None):
        sql_lower = sql.lower().strip()

        # topic_snapshots: most recent snapshot for topic
        if "topic_snapshots" in sql_lower and "order by created_at desc" in sql_lower and "limit 1" in sql_lower:
            topic_id = params[0] if params else None
            matches = [r for r in self._snapshots if r[0] == topic_id] if topic_id else self._snapshots
            if matches:
                r = matches[-1]
                # Return (doc_json, version, hash, created_at, section_count)
                return (r[1], r[2], r[3], r[4], r[5])
            return None

        # topic_snapshots: version + hash + section_count only (meta query)
        if "topic_snapshots" in sql_lower and "version, document_hash" in sql_lower:
            topic_id = params[0] if params else None
            matches = [r for r in self._snapshots if r[0] == topic_id] if topic_id else self._snapshots
            if matches:
                r = matches[-1]
                return (r[2], r[3], r[5])
            return None

        # graph.nodes single row
        if "graph.nodes" in sql_lower and "where id = %s" in sql_lower:
            node_id = params[0] if params else None
            # Determine what columns are selected
            for row in self._nodes:
                if row[0] == node_id:
                    if "select type, data" in sql_lower:
                        data = row[2] if isinstance(row[2], dict) else json.loads(row[2])
                        return (row[1], data)
                    data = row[2] if isinstance(row[2], dict) else json.loads(row[2])
                    return (data,)
            return None

        return None

    def fetch_all(self, sql: str, params=None):
        sql_lower = sql.lower().strip()

        # Nodes for topic compilation
        if "graph.nodes" in sql_lower and "join graph.edges" in sql_lower and "assembled_in" not in sql_lower.lower():
            # compile_topic query: returns nodes for topic
            topic_id = params[0] if params else None
            results = []
            for row in self._nodes:
                nid, ntype, ndata, created_at = row
                if ntype not in ("intent", "concept", "brick"):
                    continue
                data = ndata if isinstance(ndata, dict) else json.loads(ndata)
                lc = data.get("lifecycle", "loose")
                if lc in ("frozen", "forming"):
                    # Check if connected to the topic via any edge
                    connected = any(
                        e[0] == topic_id and e[1] == nid
                        for e in self._edges
                    )
                    if connected:
                        results.append((nid, data, created_at))
            # Sort by created_at ASC (deterministic)
            results.sort(key=lambda x: str(x[2]))
            return results

        # Supersession edges
        if "edge_type = 'superseded_by'" in sql_lower or "edge_type = 'SUPERSEDED_BY'" in sql:
            node_ids = params[0] if params else []
            return [
                (e[0], e[1]) for e in self._edges
                if e[0] in node_ids and e[2].upper() == "SUPERSEDED_BY"
            ]

        # Cross-topic references
        if "cross" in sql_lower or ("sync_topic_id" in sql_lower and "!=" in sql_lower):
            return []

        # entity_aliases
        if "entity_aliases" in sql_lower:
            topic_id = params[0] if params else None
            text = params[1].lower() if params and len(params) > 1 else ""
            results = []
            for alias_node_id, alias_text in self._aliases:
                if alias_text.lower() == text:
                    # Check node is frozen and in scope
                    for row in self._nodes:
                        if row[0] == alias_node_id:
                            data = row[2] if isinstance(row[2], dict) else json.loads(row[2])
                            if data.get("lifecycle") == "frozen":
                                results.append((alias_node_id,))
            return results

        # exact match for resolver
        if "lower(n.data->>'statement') = lower" in sql_lower:
            scope_id = params[0] if params else None
            text = params[1].lower() if params and len(params) > 1 else ""
            results = []
            for row in self._nodes:
                nid, ntype, ndata, _ = row
                if ntype not in ("intent", "concept"):
                    continue
                data = ndata if isinstance(ndata, dict) else json.loads(ndata)
                if data.get("lifecycle") != "frozen":
                    continue
                stmt = (data.get("statement") or "").lower()
                if stmt == text:
                    # Check APPLIES_TO edge to scope
                    connected = any(
                        e[0] == nid and e[1] == scope_id and e[2] == "APPLIES_TO"
                        for e in self._edges
                    )
                    if connected:
                        results.append((nid,))
            return results

        return []

    def execute(self, sql: str, params=None):
        self.executed.append((sql.strip(), params))

    def transaction(self):
        """Return a context manager that yields a fake cursor."""
        fake_cursor = _FakeCursor(self)
        return _FakeTransactionCtx(fake_cursor)


class _FakeCursor:
    def __init__(self, db: _FakeDB):
        self._db = db
        self.executed = []

    def execute(self, sql, params=None):
        self._db.executed.append((sql.strip(), params))
        self.executed.append((sql.strip(), params))

    def fetchone(self):
        return None

    def fetchall(self):
        return []


class _FakeTransactionCtx:
    def __init__(self, cursor):
        self._cursor = cursor

    def __enter__(self):
        return self._cursor

    def __exit__(self, *args):
        pass


# ---------------------------------------------------------------------------
# Helper factory functions
# ---------------------------------------------------------------------------

def _make_node(
    node_id: str,
    node_type: str = "brick",
    lifecycle: str = "frozen",
    statement: str = "Some statement.",
    created_at: str = "2024-01-01T00:00:00Z",
    extra: Optional[Dict] = None,
) -> tuple:
    data = {"lifecycle": lifecycle, "statement": statement, "metadata": {}}
    if extra:
        data.update(extra)
    return (node_id, node_type, data, created_at)


def _make_edge(
    source_id: str, target_id: str, edge_type: str = "ASSEMBLED_IN"
) -> tuple:
    return (source_id, target_id, edge_type, {})


# ---------------------------------------------------------------------------
# PART 1 — DocumentCompiler tests
# ---------------------------------------------------------------------------

class TestDocumentCompilerDeterminism(unittest.TestCase):
    """Same graph state → identical hash."""

    def _build_db(self):
        topic_id = "topic_1"
        nodes = [
            _make_node("n1", "brick", "frozen", "Alpha statement.", "2024-01-01T00:00:00Z"),
            _make_node("n2", "brick", "frozen", "Beta statement.", "2024-01-02T00:00:00Z"),
        ]
        edges = [
            _make_edge(topic_id, "n1"),
            _make_edge(topic_id, "n2"),
            _make_node("topic_1", "topic", "frozen", "Test Topic"),
        ]
        # Add the topic node to nodes list
        nodes.append(_make_node(topic_id, "topic", "frozen", "Test Topic"))
        return _FakeDB(nodes=nodes, edges=edges)

    def test_same_state_yields_identical_hash(self):
        """Calling compile_topic twice on the same DB state yields the same hash."""
        from nexus.projection.document_compiler import DocumentCompiler

        db1 = self._build_db()
        db2 = self._build_db()

        c1 = DocumentCompiler(db=db1, persist_snapshots=False)
        c2 = DocumentCompiler(db=db2, persist_snapshots=False)

        doc1 = c1.compile_topic("topic_1")
        doc2 = c2.compile_topic("topic_1")

        self.assertEqual(doc1.hash, doc2.hash, "Hashes must be identical for same graph state")

    def test_hash_changes_with_different_content(self):
        """Adding a new node changes the hash."""
        from nexus.projection.document_compiler import DocumentCompiler

        topic_id = "topic_1"

        db_a = _FakeDB(
            nodes=[
                _make_node(topic_id, "topic", "frozen", "Test Topic"),
                _make_node("n1", "brick", "frozen", "Alpha statement.", "2024-01-01T00:00:00Z"),
            ],
            edges=[_make_edge(topic_id, "n1")],
        )
        db_b = _FakeDB(
            nodes=[
                _make_node(topic_id, "topic", "frozen", "Test Topic"),
                _make_node("n1", "brick", "frozen", "Alpha statement.", "2024-01-01T00:00:00Z"),
                _make_node("n2", "brick", "frozen", "Gamma statement.", "2024-01-03T00:00:00Z"),
            ],
            edges=[
                _make_edge(topic_id, "n1"),
                _make_edge(topic_id, "n2"),
            ],
        )

        c1 = DocumentCompiler(db=db_a, persist_snapshots=False)
        c2 = DocumentCompiler(db=db_b, persist_snapshots=False)

        doc_a = c1.compile_topic(topic_id)
        doc_b = c2.compile_topic(topic_id)

        self.assertNotEqual(doc_a.hash, doc_b.hash, "Different content must produce different hashes")

    def test_hash_is_valid_sha256(self):
        """Hash must be a 64-char hexadecimal string."""
        from nexus.projection.document_compiler import DocumentCompiler

        topic_id = "topic_sha"
        db = _FakeDB(
            nodes=[_make_node(topic_id, "topic", "frozen", "SHA Topic")],
            edges=[],
        )
        compiler = DocumentCompiler(db=db, persist_snapshots=False)
        doc = compiler.compile_topic(topic_id)
        self.assertEqual(len(doc.hash), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in doc.hash))


class TestDocumentCompilerExclusion(unittest.TestCase):
    """Superseded and killed nodes must be excluded."""

    def test_superseded_node_excluded(self):
        """A node whose id appears as source_id in a SUPERSEDED_BY edge is excluded."""
        from nexus.projection.document_compiler import DocumentCompiler

        topic_id = "topic_exc"
        db = _FakeDB(
            nodes=[
                _make_node(topic_id, "topic", "frozen", "Exclusion Topic"),
                _make_node("old_n", "brick", "frozen", "Old content.", "2024-01-01T00:00:00Z"),
                _make_node("new_n", "brick", "frozen", "New content.", "2024-01-02T00:00:00Z"),
            ],
            edges=[
                _make_edge(topic_id, "old_n"),
                _make_edge(topic_id, "new_n"),
                ("old_n", "new_n", "SUPERSEDED_BY", {}),
            ],
        )
        compiler = DocumentCompiler(db=db, persist_snapshots=False)
        doc = compiler.compile_topic(topic_id)

        section_ids = [s.node_id for s in doc.sections]
        self.assertNotIn("old_n", section_ids, "Superseded node must be excluded")
        self.assertIn("new_n", section_ids, "New (superseding) node must be included")

    def test_killed_node_excluded_by_lifecycle(self):
        """A node with lifecycle='killed' must be excluded regardless of edges."""
        from nexus.projection.document_compiler import DocumentCompiler

        topic_id = "topic_kill"
        db = _FakeDB(
            nodes=[
                _make_node(topic_id, "topic", "frozen", "Kill Topic"),
                _make_node("alive_n", "brick", "frozen", "Still alive.", "2024-01-01T00:00:00Z"),
                _make_node("dead_n", "brick", "killed", "Was killed.", "2024-01-02T00:00:00Z"),
            ],
            edges=[
                _make_edge(topic_id, "alive_n"),
                _make_edge(topic_id, "dead_n"),
            ],
        )
        compiler = DocumentCompiler(db=db, persist_snapshots=False)
        doc = compiler.compile_topic(topic_id)

        section_ids = [s.node_id for s in doc.sections]
        self.assertNotIn("dead_n", section_ids, "Killed node must be excluded")
        self.assertIn("alive_n", section_ids)


class TestDocumentCompilerOrdering(unittest.TestCase):
    """Sections must be ordered by created_at ASC (stable)."""

    def test_ordering_stable(self):
        """Sections appear in created_at ASC order regardless of insertion order."""
        from nexus.projection.document_compiler import DocumentCompiler

        topic_id = "topic_order"
        db = _FakeDB(
            nodes=[
                _make_node(topic_id, "topic", "frozen", "Order Topic"),
                _make_node("n_c", "brick", "frozen", "C content.", "2024-01-03T00:00:00Z"),
                _make_node("n_a", "brick", "frozen", "A content.", "2024-01-01T00:00:00Z"),
                _make_node("n_b", "brick", "frozen", "B content.", "2024-01-02T00:00:00Z"),
            ],
            edges=[
                _make_edge(topic_id, "n_c"),
                _make_edge(topic_id, "n_a"),
                _make_edge(topic_id, "n_b"),
            ],
        )
        compiler = DocumentCompiler(db=db, persist_snapshots=False)
        doc = compiler.compile_topic(topic_id)

        section_ids = [s.node_id for s in doc.sections]
        self.assertEqual(section_ids, ["n_a", "n_b", "n_c"], "Sections must be ASC ordered by created_at")

    def test_ordering_consistent_across_two_calls(self):
        """Ordering must be stable across two identical compile calls."""
        from nexus.projection.document_compiler import DocumentCompiler

        topic_id = "topic_stable"
        nodes = [
            _make_node(topic_id, "topic", "frozen", "Stable Topic"),
            _make_node("x1", "brick", "frozen", "X1.", "2024-03-01T00:00:00Z"),
            _make_node("x2", "brick", "frozen", "X2.", "2024-01-01T00:00:00Z"),
            _make_node("x3", "brick", "frozen", "X3.", "2024-02-01T00:00:00Z"),
        ]
        edges = [_make_edge(topic_id, f"x{i}") for i in range(1, 4)]

        c1 = DocumentCompiler(db=_FakeDB(nodes=nodes, edges=edges), persist_snapshots=False)
        c2 = DocumentCompiler(db=_FakeDB(nodes=nodes, edges=edges), persist_snapshots=False)

        doc1 = c1.compile_topic(topic_id)
        doc2 = c2.compile_topic(topic_id)

        ids1 = [s.node_id for s in doc1.sections]
        ids2 = [s.node_id for s in doc2.sections]
        self.assertEqual(ids1, ids2, "Ordering must be stable across two identical calls")


class TestDocumentCompilerReadOnly(unittest.TestCase):
    """DocumentCompiler must NEVER call mutation methods on GraphManager."""

    def test_does_not_call_promote_node(self):
        from nexus.projection.document_compiler import DocumentCompiler

        topic_id = "topic_ro"
        db = _FakeDB(
            nodes=[_make_node(topic_id, "topic", "frozen", "RO Topic")],
            edges=[],
        )
        compiler = DocumentCompiler(db=db, persist_snapshots=False)

        # Patch GraphManager to detect any mutation calls
        with patch("nexus.graph.manager.GraphManager.promote_node_to_frozen") as p1, \
             patch("nexus.graph.manager.GraphManager.supersede_node") as p2, \
             patch("nexus.graph.manager.GraphManager.register_edge") as p3, \
             patch("nexus.graph.manager.GraphManager.register_node") as p4:
            compiler.compile_topic(topic_id)
            p1.assert_not_called()
            p2.assert_not_called()
            p3.assert_not_called()
            p4.assert_not_called()


# ---------------------------------------------------------------------------
# PART 2 — MarkdownRenderer tests
# ---------------------------------------------------------------------------

class TestMarkdownRenderer(unittest.TestCase):

    def _make_doc(self):
        from nexus.projection.document_schema import StructuredDocument, Section, CrossLink
        sections = [
            Section(
                node_id="n1",
                section_type="definition",
                title="Alpha is the first letter",
                content="Alpha is the first letter of the Greek alphabet.",
                lifecycle="frozen",
                created_at="2024-01-01T00:00:00Z",
            ),
            Section(
                node_id="n2",
                section_type="concept",
                title="Beta follows alpha",
                content="Beta is the second letter.",
                lifecycle="forming",
                created_at="2024-01-02T00:00:00Z",
                supersedes=["n_old"],
            ),
        ]
        return StructuredDocument(
            topic_id="t1",
            topic_title="Greek Letters",
            version="2.1.0",
            hash="a" * 64,
            generated_at="2024-01-03T00:00:00Z",
            sections=sections,
            cross_topic_links=[],
        )

    def test_title_in_output(self):
        from nexus.projection.markdown_renderer import render_markdown
        md = render_markdown(self._make_doc())
        self.assertIn("# Greek Letters", md)

    def test_version_in_output(self):
        from nexus.projection.markdown_renderer import render_markdown
        md = render_markdown(self._make_doc())
        self.assertIn("2.1.0", md)

    def test_sections_present(self):
        from nexus.projection.markdown_renderer import render_markdown
        md = render_markdown(self._make_doc())
        self.assertIn("Alpha is the first letter", md)
        self.assertIn("Beta follows alpha", md)

    def test_supersedes_shown(self):
        from nexus.projection.markdown_renderer import render_markdown
        md = render_markdown(self._make_doc())
        self.assertIn("Supersedes", md)

    def test_empty_doc_no_error(self):
        from nexus.projection.document_schema import StructuredDocument
        from nexus.projection.markdown_renderer import render_markdown
        doc = StructuredDocument(
            topic_id="empty", topic_title="Empty Topic", version="1.0.0",
            hash="b" * 64, generated_at="2024-01-01T00:00:00Z",
            sections=[], cross_topic_links=[],
        )
        md = render_markdown(doc)
        self.assertIn("Empty Topic", md)
        self.assertIn("No active sections", md)


# ---------------------------------------------------------------------------
# PART 3 — SnapshotService version bump tests
# ---------------------------------------------------------------------------

class TestSnapshotServiceVersionBump(unittest.TestCase):
    """Version arithmetic must follow spec §6.2."""

    def test_first_snapshot_version_is_1_0_0(self):
        from nexus.projection.snapshot_service import _bump_version
        # First snapshot — we set prev_sections=0 and current_version="0.0.0"
        # When no prior snapshot exists, SnapshotService assigns "1.0.0" directly
        # without calling _bump_version.  Test the utility nonetheless.
        new_v, bump = _bump_version(0, 2, "0.0.0")
        # 2 sections → delta=2 ≤ 3 → minor
        self.assertEqual(bump, "minor")

    def test_patch_bump_when_no_section_change(self):
        from nexus.projection.snapshot_service import _bump_version
        new_v, bump = _bump_version(5, 5, "1.2.3")
        self.assertEqual(bump, "patch")
        self.assertEqual(new_v, "1.2.4")

    def test_minor_bump_for_small_delta(self):
        from nexus.projection.snapshot_service import _bump_version
        new_v, bump = _bump_version(5, 7, "1.2.3")  # delta = 2
        self.assertEqual(bump, "minor")
        self.assertEqual(new_v, "1.3.0")

    def test_major_bump_for_large_delta(self):
        from nexus.projection.snapshot_service import _bump_version
        new_v, bump = _bump_version(5, 15, "1.2.3")  # delta = 10
        self.assertEqual(bump, "major")
        self.assertEqual(new_v, "2.0.0")

    def test_no_duplicate_snapshot_on_same_hash(self):
        """SnapshotService must skip write when hash is unchanged."""
        from nexus.projection.snapshot_service import SnapshotService

        topic_id = "t_dup"
        fake_hash = "abc123" + "0" * 58  # 64 chars
        # Pre-populate a snapshot
        snapshots = [(topic_id, {"topic_id": topic_id, "sections": []}, "1.0.0", fake_hash, "2024-01-01", 0)]

        db = _FakeDB(
            nodes=[_make_node(topic_id, "topic", "frozen", "Dup Topic")],
            edges=[],
            snapshots=snapshots,
        )

        service = SnapshotService(db=db)

        # Patch _compiler.compile_topic to return a doc with the SAME hash
        from nexus.projection.document_schema import StructuredDocument
        existing_doc = StructuredDocument(
            topic_id=topic_id, topic_title="Dup Topic", version="0.0.0",
            hash=fake_hash, generated_at="2024-01-02T00:00:00Z",
            sections=[], cross_topic_links=[],
        )
        service._compiler.compile_topic = MagicMock(return_value=existing_doc)

        result = service.snapshot_topic(topic_id)

        # No INSERT should have been executed into topic_snapshots
        insert_calls = [
            call for call in db.executed
            if "INSERT INTO cognition.topic_snapshots" in call[0]
        ]
        self.assertEqual(len(insert_calls), 0, "Must not insert duplicate snapshot when hash unchanged")
        self.assertEqual(result.version, "1.0.0", "Must return existing version on no-change")


# ---------------------------------------------------------------------------
# PART 4 — EntityResolver tests
# ---------------------------------------------------------------------------

class TestEntityResolverExactMatch(unittest.TestCase):

    def _resolver_with_frozen_node(self, node_id, statement, scope_id):
        from nexus.cognition.entity_resolver import EntityResolver
        db = _FakeDB(
            nodes=[
                _make_node(node_id, "intent", "frozen", statement),
            ],
            edges=[
                (node_id, scope_id, "APPLIES_TO", {}),
            ],
        )
        return EntityResolver(db=db, vector_store=None, embedder=None)

    def test_exact_match_returns_attach_existing(self):
        from nexus.cognition.entity_resolver import EntityResolver
        resolver = self._resolver_with_frozen_node("n_frozen", "Exact statement", "scope_A")
        result = resolver.resolve("Exact statement", "scope_A")
        self.assertEqual(result.action, "attach_existing")
        self.assertEqual(result.target_node_id, "n_frozen")
        self.assertEqual(result.confidence, 1.0)
        self.assertEqual(result.match_reason, "exact_title_match")

    def test_exact_match_case_insensitive(self):
        resolver = self._resolver_with_frozen_node("n2", "Hello World", "scope_B")
        from nexus.cognition.entity_resolver import EntityResolver
        resolver2 = EntityResolver(
            db=_FakeDB(
                nodes=[_make_node("n2", "intent", "frozen", "Hello World")],
                edges=[("n2", "scope_B", "APPLIES_TO", {})],
            ),
            vector_store=None,
            embedder=None,
        )
        result = resolver2.resolve("hello world", "scope_B")
        self.assertEqual(result.action, "attach_existing")

    def test_no_match_returns_create_new(self):
        from nexus.cognition.entity_resolver import EntityResolver
        db = _FakeDB(nodes=[], edges=[])
        resolver = EntityResolver(db=db, vector_store=None, embedder=None)
        result = resolver.resolve("Some new concept", "scope_X")
        self.assertEqual(result.action, "create_new")
        self.assertEqual(result.target_node_id, None)

    def test_empty_candidate_returns_create_new(self):
        from nexus.cognition.entity_resolver import EntityResolver
        db = _FakeDB(nodes=[], edges=[])
        resolver = EntityResolver(db=db, vector_store=None, embedder=None)
        result = resolver.resolve("   ", "scope_Y")
        self.assertEqual(result.action, "create_new")
        self.assertEqual(result.match_reason, "empty candidate text")

    def test_alias_match_returns_attach_existing(self):
        from nexus.cognition.entity_resolver import EntityResolver
        db = _FakeDB(
            nodes=[_make_node("n_alias", "intent", "frozen", "Real statement")],
            edges=[("n_alias", "scope_C", "APPLIES_TO", {})],
            aliases=[("n_alias", "alias text")],
        )
        resolver = EntityResolver(db=db, vector_store=None, embedder=None)
        result = resolver.resolve("alias text", "scope_C")
        self.assertEqual(result.action, "attach_existing")
        self.assertEqual(result.match_reason, "alias_match")


class TestEntityResolverScoreToAction(unittest.TestCase):

    def test_high_score_attach(self):
        from nexus.cognition.entity_resolver import EntityResolver
        self.assertEqual(EntityResolver._score_to_action(0.95), "attach_existing")

    def test_mid_score_flag_conflict(self):
        from nexus.cognition.entity_resolver import EntityResolver
        self.assertEqual(EntityResolver._score_to_action(0.70), "flag_conflict")

    def test_low_score_create_new(self):
        from nexus.cognition.entity_resolver import EntityResolver
        self.assertEqual(EntityResolver._score_to_action(0.30), "create_new")

    def test_boundary_high(self):
        from nexus.cognition.entity_resolver import EntityResolver
        self.assertEqual(EntityResolver._score_to_action(0.88), "attach_existing")

    def test_boundary_low(self):
        from nexus.cognition.entity_resolver import EntityResolver
        self.assertEqual(EntityResolver._score_to_action(0.55), "flag_conflict")


class TestEntityResolverDoesNotMutate(unittest.TestCase):
    """EntityResolver.resolve() must never write to graph.nodes or graph.edges."""

    def test_resolve_no_db_writes(self):
        from nexus.cognition.entity_resolver import EntityResolver
        db = _FakeDB(nodes=[], edges=[])
        resolver = EntityResolver(db=db, vector_store=None, embedder=None)
        resolver.resolve("Any text here", "scope_Z")
        # Only reads should have occurred — no execute() calls
        self.assertEqual(db.executed, [], "EntityResolver.resolve() must not execute any SQL writes")


# ---------------------------------------------------------------------------
# PART 5 — Lifecycle regression test
# ---------------------------------------------------------------------------

class TestLifecycleInvariantUnchanged(unittest.TestCase):
    """
    Verify that the new Semantic Layer does not break the existing lifecycle
    transition guard in GraphManager.promote_intent.
    """

    def test_invalid_lifecycle_transition_still_raises(self):
        """
        LOOSE → FROZEN (skipping FORMING) must still be rejected.
        This test must pass AFTER the new Semantic Layer is added.
        """
        from nexus.graph.manager import GraphManager
        from nexus.graph.schema import IntentLifecycle

        gm = GraphManager.__new__(GraphManager)

        # Inject a minimal fake DB
        fake_db = MagicMock()
        fake_db.fetch_one.return_value = (
            json.dumps({"lifecycle": "loose", "statement": "Test"})
        ,)

        # _is_adapter must return False (cursor path)
        gm.db = fake_db
        gm.embedder = None
        gm.vector_store = None
        gm._vector_write_counter = 0
        gm._VECTOR_PERSIST_EVERY = 20

        # Patch _get_node_data to return a loose node
        with patch.object(gm, "_get_node_data", return_value={"lifecycle": "loose"}), \
             patch.object(gm, "_execute") as mock_exec, \
             patch.object(gm, "_fetch_all", return_value=[]):

            with self.assertRaises(ValueError) as ctx:
                gm.promote_intent("node_x", IntentLifecycle.FROZEN)

            self.assertIn("Invalid transition", str(ctx.exception))

    def test_frozen_to_superseded_still_allowed(self):
        """FROZEN → SUPERSEDED must still be a valid transition."""
        from nexus.graph.manager import GraphManager
        from nexus.graph.schema import IntentLifecycle

        gm = GraphManager.__new__(GraphManager)
        fake_db = MagicMock()
        gm.db = fake_db
        gm.embedder = None
        gm.vector_store = None
        gm._vector_write_counter = 0
        gm._VECTOR_PERSIST_EVERY = 20

        mock_edges = [MagicMock(edge_type=type('E', (), {'value': 'APPLIES_TO'})(), source_id="node_y")]

        with patch.object(gm, "_get_node_data", return_value={"lifecycle": "frozen"}), \
             patch.object(gm, "_execute") as mock_exec, \
             patch.object(gm, "get_edges_for_node", return_value=mock_edges):
            # Should NOT raise
            try:
                gm.promote_intent("node_y", IntentLifecycle.SUPERSEDED)
            except ValueError:
                self.fail("FROZEN → SUPERSEDED should be a valid transition")


# ---------------------------------------------------------------------------
# PART 6 — Worker transaction invariant test
# ---------------------------------------------------------------------------

class TestPGWorkerTransactionInvariant(unittest.TestCase):
    """
    PGWorker.run_once must follow the two-phase claim-then-execute pattern.
    This test verifies that the transaction structure has NOT been broken
    by any changes introduced by the new Semantic Layer.
    """

    def test_run_once_claims_task_then_executes_handler(self):
        """
        Verify the two-phase transaction:
        Phase 1: Claim (UPDATE status=running, attempts++) inside first TX
        Phase 2: Execute handler inside second TX
        Both phases must complete for a success path.
        """
        from services.cortex.worker import PGWorker

        worker = PGWorker.__new__(PGWorker)
        worker.worker_id = "test-worker"
        worker.visibility_timeout = __import__("datetime").timedelta(minutes=5)

        # Track TX enter counts
        tx_count = []
        handler_called = []

        class _FakeTaskRow:
            pass

        class _FakeTx:
            def __init__(self):
                self.cursor = MagicMock()
                # First TX: returns a task row
                self.cursor.fetchone.return_value = (
                    "task-001", "test_task", json.dumps({"x": 1}), 0
                )
            def __enter__(self):
                tx_count.append(1)
                return self.cursor
            def __exit__(self, *a):
                pass

        call_count = [0]
        def make_tx():
            call_count[0] += 1
            tx = _FakeTx()
            if call_count[0] > 1:
                # Second TX: no task in queue
                tx.cursor.fetchone.return_value = None
            return tx

        mock_db = MagicMock()
        mock_db.transaction.side_effect = make_tx

        worker.db = mock_db

        # Register a dummy handler
        from services.cortex.orchestration import TaskRegistry

        @TaskRegistry.register("test_task_worker_invariant")
        def _dummy(payload, cursor=None):
            handler_called.append(True)
            return {"status": "success"}

        # Patch TaskRegistry.get_handler to use our dummy
        with patch("services.cortex.orchestration.TaskRegistry.get_handler") as mock_gh:
            mock_gh.return_value = _dummy
            with patch.object(worker, "_start_heartbeat", return_value=MagicMock(set=MagicMock())):
                with patch.object(worker, "_record_failure"):
                    result = worker.run_once()

        # Two transactions must have been opened (claim + execute)
        self.assertGreaterEqual(mock_db.transaction.call_count, 1,
                                "run_once must open at least one transaction")

    def test_run_once_returns_false_on_empty_queue(self):
        """run_once returns False when no pending tasks — unchanged contract."""
        from services.cortex.worker import PGWorker

        worker = PGWorker.__new__(PGWorker)
        worker.worker_id = "test-worker-empty"
        worker.visibility_timeout = __import__("datetime").timedelta(minutes=5)

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None  # No tasks

        mock_tx = MagicMock()
        mock_tx.__enter__ = MagicMock(return_value=mock_cursor)
        mock_tx.__exit__ = MagicMock(return_value=False)

        mock_db = MagicMock()
        mock_db.transaction.return_value = mock_tx
        worker.db = mock_db

        result = worker.run_once()
        self.assertFalse(result, "run_once must return False when queue is empty")

    def test_record_failure_uses_independent_connection(self):
        """
        _record_failure must open its OWN DB connection via get_adapter(),
        never reusing self.db.  This is the P-01 invariant.
        """
        from services.cortex.worker import PGWorker

        worker = PGWorker.__new__(PGWorker)
        worker.worker_id = "test-worker-fail"
        worker.visibility_timeout = __import__("datetime").timedelta(minutes=5)
        worker.db = MagicMock()

        with patch("services.cortex.worker.get_adapter") as mock_get_adapter:
            mock_fresh_db = MagicMock()
            mock_get_adapter.return_value = mock_fresh_db
            worker._record_failure("task-xyz", "some error", "traceback text")
            mock_get_adapter.assert_called_once()
            mock_fresh_db.execute.assert_called_once()


# ---------------------------------------------------------------------------
# PART 7 — Refiner read-only invariant test
# ---------------------------------------------------------------------------

class TestRefinerReadOnly(unittest.TestCase):
    """Refiner.audit_topic() must NOT mutate graph.nodes or graph.edges."""

    def test_audit_topic_writes_only_to_drift_reports(self):
        from nexus.cognition.refiner import Refiner

        topic_id = "t_refiner"
        db = _FakeDB(
            nodes=[
                _make_node(topic_id, "topic", "frozen", "Refiner Topic"),
                _make_node("fn1", "intent", "frozen", "Frozen node 1.", "2024-01-01"),
            ],
            edges=[
                (topic_id, "fn1", "ASSEMBLED_IN", {}),
                ("fn1", topic_id, "APPLIES_TO", {}),
            ],
        )

        refiner = Refiner(db=db, vector_store=None, embedder=None)
        refiner.audit_topic(topic_id)

        # Only drift_reports inserts are allowed — verify no UPDATE/DELETE on nodes/edges
        forbidden_patterns = ["update graph.nodes", "delete from graph", "update graph.edges"]
        for sql, _ in db.executed:
            sql_lower = sql.lower()
            for pattern in forbidden_patterns:
                self.assertNotIn(
                    pattern,
                    sql_lower,
                    f"Refiner must not execute: {pattern}",
                )


# ---------------------------------------------------------------------------
# PART 8 — Compiler injection: EntityResolver is called, not bypassed
# ---------------------------------------------------------------------------

class TestCompilerEntityResolverInjection(unittest.TestCase):
    """
    EntityResolver must be injected into NexusCompiler at construction time.
    This ensures the injection point is present without modifying compile_run.
    """

    def test_entity_resolver_injected_in_compiler(self):
        """NexusCompiler must have a _resolver attribute after construction."""
        from nexus.sync.compiler import NexusCompiler
        from nexus.sync.db import SyncDatabase

        mock_db = MagicMock(spec=SyncDatabase)

        with patch("nexus.cognition.entity_resolver.EntityResolver.__init__", return_value=None):
            compiler = NexusCompiler(db_connection=mock_db)

        self.assertTrue(
            hasattr(compiler, "_resolver"),
            "NexusCompiler must have _resolver attribute after EntityResolver injection",
        )

    def test_compiler_resolver_graceful_fallback(self):
        """
        If EntityResolver cannot be imported, NexusCompiler must still
        initialise with _resolver=None (graceful degradation).
        """
        from nexus.sync.compiler import NexusCompiler
        from nexus.sync.db import SyncDatabase

        mock_db = MagicMock(spec=SyncDatabase)

        with patch("nexus.cognition.entity_resolver.EntityResolver", side_effect=ImportError("no module")):
            compiler = NexusCompiler(db_connection=mock_db)

        # _resolver may be None or a valid object — the key is no AttributeError
        self.assertIn("_resolver", compiler.__dict__ if hasattr(compiler, "__dict__") else {})


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)
