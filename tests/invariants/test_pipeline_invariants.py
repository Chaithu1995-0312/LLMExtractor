import unittest
import os
import sys
import shutil
import json
from unittest.mock import patch, MagicMock
from nexus.sync.runner import run_sync
from nexus.walls.builder import build_walls
from nexus.bricks.extractor import extract_bricks_from_file

class TestPipelineInvariants(unittest.TestCase):
    def setUp(self):
        self.test_dir = "tests/temp_pipeline_test"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)
        
    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_missing_conversations_json_aborts_sync(self):
        """❌ Missing conversations.json → sync aborts (Fail-closed)"""
        with self.assertRaises(SystemExit) as cm:
            run_sync("non_existent_file.json", self.test_dir)
        self.assertEqual(cm.exception.code, 1)

    def test_nondeterministic_wall_output_fail(self):
        """❌ Non-deterministic wall output → FAIL"""
        # Create dummy tree files
        trees = []
        for i in range(3):
            tree_path = os.path.join(self.test_dir, f"tree_{i}.json")
            with open(tree_path, "w") as f:
                json.dump({
                    "conversation_id": f"conv_{i}",
                    "title": f"Title {i}",
                    "messages": [{"message_id": "1", "role": "user", "content": "hello", "model_name": "gpt-4"}]
                }, f)
            trees.append(tree_path)
            
        # Run 1
        output1 = os.path.join(self.test_dir, "output1")
        build_walls(trees, output1)
        
        # Run 2
        output2 = os.path.join(self.test_dir, "output2")
        build_walls(trees, output2)
        
        # Compare
        files1 = sorted(os.listdir(output1))
        files2 = sorted(os.listdir(output2))
        
        self.assertEqual(files1, files2, "Wall file lists must be identical")
        
        for f in files1:
            with open(os.path.join(output1, f), "r") as f1, open(os.path.join(output2, f), "r") as f2:
                self.assertEqual(f1.read(), f2.read(), f"Content of {f} must be identical across runs")

    def test_brick_span_mismatch_fail(self):
        """❌ Brick span mismatch → FAIL"""
        tree_path = os.path.join(self.test_dir, "test_tree.json")
        msg_id = "target_msg_123"
        content = "Line 1\n\nLine 2"
        with open(tree_path, "w") as f:
            json.dump({
                "conversation_id": "conv_1",
                "messages": [{"message_id": msg_id, "role": "user", "content": content, "model_name": "gpt-4"}]
            }, f)
            
        brick_file = extract_bricks_from_file(tree_path, self.test_dir)
        with open(brick_file, "r") as f:
            bricks = json.load(f)
            
        self.assertEqual(len(bricks), 2)
        self.assertEqual(bricks[0]["source_span"]["message_id"], msg_id)
        self.assertEqual(bricks[0]["source_span"]["block_index"], 0)
        self.assertEqual(bricks[1]["source_span"]["block_index"], 1)

if __name__ == "__main__":
    unittest.main()
