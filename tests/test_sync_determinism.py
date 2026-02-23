import unittest
import json
import hashlib
from unittest.mock import MagicMock, patch
from nexus.sync.db import SyncDatabase, AppendViolationError
from nexus.sync.compiler import NexusCompiler

class TestSyncDeterminism(unittest.TestCase):
    def setUp(self):
        # Mock DB connection
        self.mock_db = MagicMock(spec=SyncDatabase)
        self.compiler = NexusCompiler(self.mock_db)
        
        # Mock GraphManager for Audit Logging
        self.compiler.graph_manager = MagicMock()

        # Test Data
        self.run_id = "test_run_001"
        self.topic_id = "test_topic_A"
        self.topic_def = {"display_name": "Test Topic"}
        
        self.message_1 = {
            "id": "msg_1",
            "role": "user",
            "content": "Hello world"
        }
        self.message_2 = {
            "id": "msg_2", 
            "role": "assistant",
            "content": "Hello user"
        }
        
        # Setup mocks
        self.mock_db.get_run.return_value = {
            "id": self.run_id,
            "raw_content": {"messages": [self.message_1, self.message_2]},
            "last_processed_index": -1
        }
        self.mock_db.get_topic.return_value = self.topic_def
        self.mock_db.get_bricks_for_topic.return_value = [] # Start empty

    def test_canonical_normalization(self):
        """Test that newlines are normalized and hashing is byte-stable."""
        # Input with Windows line endings and trailing whitespace
        msg_windows = {
            "id": "msg_identity_test", 
            "role": "user", 
            "content": "Line 1\r\nLine 2   "
        }
        
        brick = self.compiler._materialize_message_brick(msg_windows, 0, self.run_id, self.topic_id)
        
        # Expectation: Content stored as \n AND stripped
        expected_content = "Line 1\nLine 2"
        self.assertEqual(brick["content"], expected_content)
        
        # Expectation: Fingerprint is hash of stored content (which is already stripped)
        expected_fingerprint = hashlib.sha256(expected_content.encode("utf-8")).hexdigest()
        self.assertEqual(brick["fingerprint"], expected_fingerprint)
        
        # Verify it matches Linux input without trailing space
        msg_linux = {
            "id": "msg_identity_test", 
            "role": "user",
            "content": "Line 1\nLine 2"
        }
        brick_linux = self.compiler._materialize_message_brick(msg_linux, 0, self.run_id, self.topic_id)
        
        # IDs and fingerprints must match
        self.assertEqual(brick["id"], brick_linux["id"]) 
        self.assertEqual(brick["fingerprint"], brick_linux["fingerprint"])

    def test_atomic_save_call(self):
        """Test that the compiler calls the atomic save method."""
        # We need to ensure compile_run actually processes something. 
        # The mock setup in setUp() provides 2 messages.
        
        self.compiler.compile_run(self.run_id, self.topic_id)
        
        # Check that save_brick_atomic was called
        self.assertTrue(self.mock_db.save_brick_atomic.called)
        self.assertEqual(self.mock_db.save_brick_atomic.call_count, 2) # 2 messages in setup
        
        # Verify strict stripping behavior via the call args
        # The messages in setUp have no trailing whitespace, so let's verify canonical content is passed
        calls = self.mock_db.save_brick_atomic.call_args_list
        brick_1 = calls[0][0][0]
        self.assertEqual(brick_1["content"], "Hello world") # Stripped & Normalized

if __name__ == '__main__':
    unittest.main()
