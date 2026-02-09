import unittest
import json
from nexus.sync.compiler import NexusCompiler, MAX_MESSAGES_PER_BATCH, MAX_CHARS_PER_BATCH
from nexus.sync.db import SyncDatabase

class MockLLM:
    def generate(self, system, user):
        # Always return empty pointers for this test
        return json.dumps({"extracted_pointers": []})

class TestCompilerPerformance(unittest.TestCase):
    def setUp(self):
        self.db = SyncDatabase(":memory:")
        self.llm = MockLLM()
        self.compiler = NexusCompiler(self.db, self.llm)

    def test_pre_filter_rejection(self):
        """Test that structural rejection works."""
        raw_content = {
            "messages": [
                {"role": "user", "content": "Helpful message with must rule"}, # Keep
                {"role": "user", "content": ""}, # Reject (empty)
                {"role": "assistant", "content": "Hallucination Artifact follow-up"}, # Reject (artifact)
                {"role": "assistant", "content": "Normal assistant message"}, # Reject (no signal)
                {"role": "user", "content": "Another rule should be followed"} # Keep
            ]
        }
        filtered, max_idx = self.compiler._pre_filter_nodes(raw_content, last_processed=-1)
        
        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0]["content"], "Helpful message with must rule")
        self.assertEqual(filtered[1]["content"], "Another rule should be followed")
        self.assertEqual(max_idx, 4)

    def test_batching_logic(self):
        """Test that messages are correctly batched."""
        messages = [
            {"role": "user", "content": "msg 1", "_original_index": 0},
            {"role": "user", "content": "msg 2", "_original_index": 1},
            {"role": "user", "content": "msg 3", "_original_index": 2},
            {"role": "user", "content": "msg 4", "_original_index": 3},
            {"role": "user", "content": "msg 5", "_original_index": 4},
            {"role": "user", "content": "msg 6", "_original_index": 5},
        ]
        
        # With MAX_MESSAGES_PER_BATCH = 5, we expect 2 batches (5 and 1)
        batches = self.compiler._build_batches(messages)
        self.assertEqual(len(batches), 2)
        self.assertEqual(len(batches[0]), 5)
        self.assertEqual(len(batches[1]), 1)

    def test_batching_char_limit(self):
        """Test that char limit forces a new batch."""
        # The limit is 8000. 
        # But we truncate content to 2000.
        # json.dumps({"role": "user", "content": "a"*2000, "_original_index": 0}) is approx 2050 chars.
        # 4 such messages should be ~8200 chars, forcing a split if MAX_CHARS_PER_BATCH is 8000.
        long_content = "a" * 3000 # Will be truncated to 2000
        messages = [
            {"role": "user", "content": long_content, "_original_index": 0},
            {"role": "user", "content": long_content, "_original_index": 1},
            {"role": "user", "content": long_content, "_original_index": 2},
            {"role": "user", "content": long_content, "_original_index": 3},
            {"role": "user", "content": long_content, "_original_index": 4},
        ]
        
        batches = self.compiler._build_batches(messages)
        self.assertTrue(len(batches) >= 2) 

if __name__ == "__main__":
    unittest.main()
