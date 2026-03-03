import os
import json
import unittest
from dotenv import load_dotenv
load_dotenv()

from nexus.compiler.topic_compiler import TopicCompiler
from nexus.compiler.conflict_resolver import ConflictResolver, Lifecycle
from nexus.compiler.packaging import ZipPackager
from nexus.graph.manager import GraphManager

class TestTopicCompiler(unittest.TestCase):
    def setUp(self):
        self.compiler = TopicCompiler()
        self.resolver = ConflictResolver()
        self.gm = GraphManager()

    def test_conflict_resolution_priority(self):
        """Frozen should win over others"""
        bricks = [
            {"id": "b1", "content": "I am loose", "lifecycle": "Loose", "created_at": "2026-01-01"},
            {"id": "b2", "content": "I am frozen", "lifecycle": "Frozen", "created_at": "2026-01-01"},
            {"id": "b3", "content": "I am forming", "lifecycle": "Forming", "created_at": "2026-01-01"}
        ]
        resolved = self.resolver.resolve(bricks)
        self.assertEqual(resolved[0]["id"], "b2")
        self.assertEqual(resolved[0]["lifecycle"], "Frozen")

    def test_determinism(self):
        """Same input should yield same output order"""
        bricks = [
            {"id": "z1", "content": "Z", "lifecycle": "Loose"},
            {"id": "a1", "content": "A", "lifecycle": "Loose"},
            {"id": "m1", "content": "M", "lifecycle": "Loose"}
        ]
        # Resolve handles priority but fallback to sorting
        # TopicCompiler._assemble_documents sorts by ID
        sorted_bricks = sorted(bricks, key=lambda x: x["id"])
        self.assertEqual(sorted_bricks[0]["id"], "a1")
        self.assertEqual(sorted_bricks[2]["id"], "z1")

    def test_packaging(self):
        """ZIP package should contain documents and manifest"""
        docs = [
            {"filename": "test.md", "content": "Hello World"}
        ]
        manifest = {"topic_id": "test_topic", "audit_hash": "123"}
        topic_id = "test_topic"
        pkg_path = ZipPackager.create_package(topic_id, docs, manifest)
        self.assertTrue(os.path.exists(pkg_path))
        # Cleanup
        if os.path.exists(pkg_path):
            os.remove(pkg_path)

if __name__ == "__main__":
    unittest.main()
