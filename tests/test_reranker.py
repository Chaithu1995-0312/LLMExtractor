import unittest
import sys
import os
import shutil
import tempfile
import json
from unittest.mock import MagicMock, patch

# Use the properly installed nexus package
# For tests running from root, ensure src is in sys.path if not installed
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from nexus.rerank.heuristic import HeuristicReranker
from nexus.rerank.orchestrator import RerankOrchestrator

class TestReranker(unittest.TestCase):
    def setUp(self):
        self.candidates = [
            {"brick_id": "1", "brick_text": "apple pie recipe", "base_confidence": 0.5},
            {"brick_id": "2", "brick_text": "banana bread", "base_confidence": 0.6},
            {"brick_id": "3", "brick_text": "irrelevant text", "base_confidence": 0.4},
        ]
        self.query = "apple"

    def test_heuristic_ranking(self):
        reranker = HeuristicReranker()
        results = reranker.rank(self.query, [c.copy() for c in self.candidates])
        
        # Apple pie should be first because of "apple" overlap
        self.assertEqual(results[0]["brick_id"], "1")
        self.assertEqual(results[0]["reranker_used"], "heuristic")
        self.assertTrue(results[0]["final_score"] > 0)

    def test_orchestrator_fallback(self):
        # Patch LlmReranker and CrossEncoderReranker to fail on init or usage
        with patch('nexus.rerank.orchestrator.LlmReranker', side_effect=ImportError("Mock missing LLM")), \
             patch('nexus.rerank.orchestrator.CrossEncoderReranker', side_effect=ImportError("Mock missing CrossEncoder")):
             
            orch = RerankOrchestrator()
            # Should fall back to Heuristic
            results = orch.rerank(self.query, [c.copy() for c in self.candidates])
            
            self.assertEqual(results[0]["reranker_used"], "heuristic")
            self.assertEqual(results[0]["brick_id"], "1")

    def test_invariants(self):
        # Count check
        orch = RerankOrchestrator()
        original_count = len(self.candidates)
        results = orch.rerank(self.query, [c.copy() for c in self.candidates])
        
        self.assertEqual(len(results), original_count)
        
        # Check IDs
        result_ids = set(r["brick_id"] for r in results)
        original_ids = set(c["brick_id"] for c in self.candidates)
        self.assertEqual(result_ids, original_ids)

if __name__ == '__main__':
    unittest.main()
