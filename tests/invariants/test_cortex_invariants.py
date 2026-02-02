import unittest
import os
import json
import shutil
from unittest.mock import patch
from cortex.api import CortexAPI

class TestCortexInvariants(unittest.TestCase):
    def setUp(self):
        self.test_dir = "tests/temp_cortex_test"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)
        self.audit_log = os.path.join(self.test_dir, "audit.jsonl")
        self.api = CortexAPI(audit_log_path=self.audit_log)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_vector_hit_without_raw_reload_blocks(self):
        """❌ Vector hit without raw reload → Cortex BLOCK"""
        # Mocking _reload_source_text to fail
        with patch.object(CortexAPI, '_reload_source_text', return_value=""):
            result = self.api.generate("user1", "agent1", "query", ["brick1"])
            self.assertEqual(result["status"], "blocked")
            self.assertIn("Violation", result["error"])

    def test_llm_call_without_audit_row_fail(self):
        """❌ Any LLM call without audit row → FAIL"""
        # Count audit rows before
        initial_count = 0
        if os.path.exists(self.audit_log):
            with open(self.audit_log, "r") as f:
                initial_count = len(f.readlines())
        
        self.api.generate("user1", "agent1", "query", ["brick1"])
        
        # Count after
        with open(self.audit_log, "r") as f:
            after_count = len(f.readlines())
            
        self.assertEqual(after_count, initial_count + 1, "Audit row must be created for every generation call")

    def test_direct_llm_sdk_usage_outside_cortex_fail(self):
        """❌ Direct LLM SDK usage outside Cortex → FAIL"""
        # This test uses static analysis to check for forbidden imports in nexus-cli
        forbidden = ["openai", "anthropic", "google.generativeai"]
        nexus_dir = "nexus-cli"
        violations = []
        
        for root, dirs, files in os.walk(nexus_dir):
            for file in files:
                if file.endswith(".py"):
                    path = os.path.join(root, file)
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                        for sdk in forbidden:
                            if f"import {sdk}" in content or f"from {sdk}" in content:
                                violations.append(f"{path}: {sdk}")
        
        self.assertEqual(len(violations), 0, f"Violations found: {violations}")

if __name__ == "__main__":
    unittest.main()
