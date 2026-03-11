import unittest
import json
import time
from unittest.mock import MagicMock, patch
from nexus.cache.decision_cache import DecisionCache

class TestDecisionCache(unittest.TestCase):
    def setUp(self):
        with patch('nexus.cache.decision_cache.get_adapter') as mock_get_adapter:
            mock_db = MagicMock()
            mock_get_adapter.return_value = mock_db
            self.cache = DecisionCache()
            self.cache.db = mock_db # Ensure our reference matches what was injected
            self.cache.enabled = True

    def test_compute_key_determinism(self):
        k1 = self.cache.compute_key("agent1", " sys ", " user ", ["a", "b"])
        k2 = self.cache.compute_key("agent1", "sys", "user", ["b", "a"]) # Different order list
        
        # List order matters in my implementation? 
        # "context": sorted(context_ids) if context_ids else []
        # So order should NOT matter for the key if I sorted it.
        
        self.assertEqual(k1, k2)
        
    def test_compute_key_normalization(self):
        k1 = self.cache.compute_key("agent1", "Hello", "World")
        k2 = self.cache.compute_key("agent1", " hello ", " world ")
        self.assertEqual(k1, k2)

    def test_get_hit(self):
        # Mock DB return
        expected_result = {"foo": "bar"}
        self.cache.db.fetch_one.return_value = [json.dumps(expected_result)]
        
        result = self.cache.get("some_key")
        self.assertEqual(result, expected_result)
        
        # Verify query structure
        args = self.cache.db.fetch_one.call_args
        self.assertIn("SELECT result", args[0][0])
        self.assertIn("ttl_hours", args[0][0])

    def test_get_miss(self):
        self.cache.db.fetch_one.return_value = None
        result = self.cache.get("missing_key")
        self.assertIsNone(result)

    def test_set(self):
        self.cache.set("key1", "agent1", {"data": 123})
        
        # Verify execute called
        self.cache.db.execute.assert_called_once()
        args = self.cache.db.execute.call_args
        query = args[0][0]
        params = args[0][1]
        
        self.assertIn("INSERT INTO graph.decision_cache", query)
        self.assertEqual(params[0], "key1")
        self.assertEqual(params[1], "agent1")
        self.assertEqual(params[2], '{"data": 123}')

if __name__ == '__main__':
    unittest.main()
