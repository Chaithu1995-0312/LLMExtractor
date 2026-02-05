import sys
import os
import json
import unittest

# Add repo root to path
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(repo_root)
sys.path.append(os.path.join(repo_root, "services", "cortex"))

from services.cortex.server import app
from nexus.graph.manager import GraphManager

class TestServerGraph(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        self.manager = GraphManager()

    def test_graph_index(self):
        """Test retrieving the graph index."""
        rv = self.client.get('/jarvis/graph-index')
        self.assertEqual(rv.status_code, 200)
        data = rv.get_json()
        self.assertIn("nodes", data)
        self.assertIn("edges", data)
        self.assertIn("index_content", data)
        self.assertIn("anchor_overrides", data)
        
        # Verify nodes format
        if data["nodes"]:
            node = data["nodes"][0]
            self.assertIn("id", node)
            self.assertIn("type", node)
            self.assertIn("created_at", node)
        
        # Verify edges format
        if data["edges"]:
            edge = data["edges"][0]
            self.assertIn("source", edge)
            self.assertIn("target", edge)
            self.assertIn("type", edge)

    def test_anchor_promote(self):
        """Test promoting a brick (creating anchor)."""
        brick_id = "test_brick_123"
        self.manager.register_node("brick", brick_id, {"content": "test"})
        
        rv = self.client.post('/jarvis/anchor', json={
            "brick_id": brick_id,
            "action": "promote"
        })
        self.assertEqual(rv.status_code, 200)
        resp = rv.get_json()
        self.assertEqual(resp["status"], "success")
        self.assertEqual(resp["brick_id"], brick_id)
        self.assertEqual(resp["action"], "promote")
        
        # Verify persistence
        node_data = self.manager._get_node_data(brick_id)
        self.assertTrue(node_data["anchored"])
        self.assertFalse(node_data.get("rejected", False))

        # Verify override in graph-index
        rv_index = self.client.get('/jarvis/graph-index')
        data_index = rv_index.get_json()
        overrides = data_index["anchor_overrides"]
        found = any(o["brick_id"] == brick_id and o["action"] == "promote" for o in overrides)
        self.assertTrue(found)

    def test_anchor_reject(self):
        """Test rejecting a brick."""
        brick_id = "test_brick_456"
        self.manager.register_node("brick", brick_id, {"content": "test"})
        
        rv = self.client.post('/jarvis/anchor', json={
            "brick_id": brick_id,
            "action": "reject"
        })
        self.assertEqual(rv.status_code, 200)
        
        node_data = self.manager._get_node_data(brick_id)
        self.assertFalse(node_data.get("anchored", False))
        self.assertTrue(node_data["rejected"])

if __name__ == "__main__":
    unittest.main()
