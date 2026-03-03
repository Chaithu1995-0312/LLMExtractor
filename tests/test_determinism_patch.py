
import unittest
import hashlib
import sys
import os
from io import BytesIO

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))
from nexus.compiler.packaging import ZipPackager

class TestDeterminism(unittest.TestCase):
    def test_in_memory_zip_determinism(self):
        topic_id = "test_topic"
        documents = [
            {"filename": "b.md", "content": "content b"},
            {"filename": "a.md", "content": "content a"},
            {"filename": "c.md", "content": "content c"}
        ]
        
        # First run
        buf1 = ZipPackager.create_in_memory_package(topic_id, documents)
        data1 = buf1.getvalue()
        hash1 = hashlib.sha256(data1).hexdigest()
        
        # Second run
        buf2 = ZipPackager.create_in_memory_package(topic_id, documents)
        data2 = buf2.getvalue()
        hash2 = hashlib.sha256(data2).hexdigest()
        
        self.assertEqual(hash1, hash2, "ZIP output is not byte-identical across runs")
        print(f"Determinism confirmed. Hash: {hash1}")

if __name__ == "__main__":
    unittest.main()
