import unittest
import json
import os
import sys
from pathlib import Path

# Add the parent directory to sys.path to find ollama_batch_worker
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ollama_batch_worker import process_shard, OUT_DIR, SHARD_DIR

class TestOllamaWorker(unittest.TestCase):
    def setUp(self):
        # Ensure directories exist
        Path(SHARD_DIR).mkdir(exist_ok=True)
        Path(OUT_DIR).mkdir(exist_ok=True)
        
        # Create a single test shard
        self.test_shard_path = Path(SHARD_DIR) / "shard_9999.jsonl"
        self.test_data = {
            "shard_id": 9999,
            "text": "User: How do I implement a custom sharder?\nAssistant: You can use tiktoken to count tokens and split JSON data into chunks."
        }
        with open(self.test_shard_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(self.test_data))

    def test_send_single_shard(self):
        print(f"\nSending single shard {self.test_shard_path} to HARDENED cognitive pipeline...")
        result = process_shard(str(self.test_shard_path))
        
        self.assertIsNotNone(result, "Pipeline result should not be None")
        self.assertIn("ollama_output", result)
        self.assertIn("accuracy_score", result)
        self.assertIn("audit", result)
        self.assertIn("shard_hash", result)
        self.assertIn("genai_review", result)
        
        audit = result["audit"]
        self.assertEqual(audit["status"], "SUCCESS")
        self.assertGreater(audit["latency_ms"], 0)
        self.assertGreater(audit["input_chars"], 0)
        
        print(f"Ollama Output: {result['ollama_output']}")
        print(f"Accuracy Score: {result['accuracy_score']}")
        print(f"Audit Block: {json.dumps(audit, indent=2)}")
        
        # Save the result for manual inspection
        output_path = Path(OUT_DIR) / "test_result_9999.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({
                "shard_id": 9999,
                **result
            }, f, indent=2)
        print(f"Hardened test result saved to {output_path}")

    def tearDown(self):
        # Clean up test shard
        if self.test_shard_path.exists():
            self.test_shard_path.unlink()

if __name__ == "__main__":
    unittest.main()
