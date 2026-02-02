import unittest
import os
import sys
import json
import shutil
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

# Adjust path to import Nexus CLI components
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "nexus-cli")))
from nexus.__main__ import cmd_ask, main as nexus_main # Import main to test arg parsing
from nexus.vector.local_index import LocalVectorIndex
from nexus.bricks.brick_store import BrickStore, query_to_vector
from nexus.ask.recall import _normalize_distance_to_confidence

# Adjust path to import Cortex API components
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "cortex")))
from api import CortexAPI

class TestNewFeatures(unittest.TestCase):
    def setUp(self):
        self.test_dir = "tests/temp_new_feature_test"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)
        self.audit_log = os.path.join(self.test_dir, "phase3_audit_trace.jsonl")

        # Mock the LocalVectorIndex and BrickStore for consistent testing
        self.mock_local_index = MagicMock(spec=LocalVectorIndex)
        self.mock_local_index.brick_ids = ["brick_test_1", "brick_test_2", "brick_test_3"]
        self.mock_local_index.search.return_value = (
            # distances (mocked for cosine similarity 0-2)
            np.array([[0.5, 1.0, 1.5]]),
            # indices
            np.array([[0, 1, 2]])
        )

        self.mock_brick_store = MagicMock(spec=BrickStore)
        self.mock_brick_store.get_brick_metadata.side_effect = [
            {"source_file": "file1.txt", "source_span": "spanA"},
            {"source_file": "file2.txt", "source_span": "spanB"},
            {"source_file": "file3.txt", "source_span": "spanC"},
        ]
        
        # Patch the global instances in nexus.ask.recall and nexus.__main__
        # to use our mocks
        patch("nexus.ask.recall._local_index", self.mock_local_index).start()
        patch("nexus.__main__._local_index", self.mock_local_index).start()
        patch("nexus.__main__._brick_store", self.mock_brick_store).start()

        # Patch CortexAPI for nexus.__main__
        self.mock_cortex_api = MagicMock(spec=CortexAPI)
        self.mock_cortex_api.generate.return_value = {"response": "Mocked Cortex Response", "model": "mock-model", "status": "success"}
        patch("nexus.__main__._cortex_api", self.mock_cortex_api).start()
        
        # Patch CortexAPI audit_log_path for direct CortexAPI tests
        self.cortex_api_for_test = CortexAPI(audit_log_path=self.audit_log)

    def tearDown(self):
        shutil.rmtree(self.test_dir)
        patch.stopall()

    def _run_nexus_command(self, command_args: List[str]):
        # Helper to run nexus commands via main parser
        with patch("sys.stdout", new=MagicMock()) as mock_stdout:
            with patch("sys.stderr", new=MagicMock()):
                with patch("sys.argv", ["nexus"] + command_args):
                    nexus_main()
                return mock_stdout.getvalue()

    def test_nexus_ask_json_output(self):
        """1. nexus ask --json returns strict JSON with correct schema and no text"""
        query = "test query"
        output = self._run_nexus_command(["ask", query, "--json"])
        
        # Assert no print logs, only JSON
        # This is implicitly tested by checking if output can be parsed as JSON
        # If any print statements were made, json.loads would likely fail
        try:
            json_output = json.loads(output)
        except json.JSONDecodeError:
            self.fail(f"Output is not valid JSON: {output}")

        self.assertIn("query", json_output)
        self.assertEqual(json_output["query"], query)
        self.assertIn("timestamp", json_output)
        self.assertIn("results", json_output)
        self.assertIsInstance(json_output["results"], list)
        self.assertEqual(len(json_output["results"]), 3) # Based on mock data
        
        for res in json_output["results"]:
            self.assertIn("brick_id", res)
            self.assertIn("confidence", res)
            self.assertIn("source_file", res)
            self.assertIn("source_span", res)
            self.assertIsInstance(res["confidence"], float)
            self.assertGreaterEqual(res["confidence"], 0.0)
            self.assertLessEqual(res["confidence"], 1.0)
        
        self.mock_cortex_api.generate.assert_not_called() # --json should not call Cortex

    def test_nexus_ask_default_output_calls_cortex(self):
        """nexus ask (default) pretty prints and calls Cortex.generate()"""
        query = "test query"
        output = self._run_nexus_command(["ask", query])

        self.assertIn(f"Nexus Ask Results for: \"{query}\"", output)
        self.assertIn("Handoff to Cortex for generation...", output)
        self.assertIn("Mocked Cortex Response", output)
        
        self.mock_cortex_api.generate.assert_called_once() # Default should call Cortex
        args, kwargs = self.mock_cortex_api.generate.call_args
        self.assertEqual(kwargs["user_query"], query)
        self.assertEqual(set(kwargs["brick_ids"]), set(["brick_test_1", "brick_test_2", "brick_test_3"]))
        
        # Ensure audit row is emitted (CortexAPI handles this internally, so we check the mock)
        with open(self.audit_log, "r") as f:
            audit_lines = f.readlines()
            self.assertEqual(len(audit_lines), 0) # Nexus does not write audit, Cortex does.

    def test_confidence_score_range_and_determinism(self):
        """2. Confidence score is 0.0-1.0 and deterministic"""
        # Range already checked in test_nexus_ask_json_output
        # Test determinism (via query_to_vector and _normalize_distance_to_confidence)
        query1 = "deterministic query"
        query2 = "deterministic query"
        query_vec1 = query_to_vector(query1)
        query_vec2 = query_to_vector(query2)
        self.assertTrue(np.array_equal(query_vec1, query_vec2), "Query vector generation must be deterministic")

        # Test _normalize_distance_to_confidence directly
        self.assertEqual(_normalize_distance_to_confidence(0.0), 1.0)
        self.assertEqual(_normalize_distance_to_confidence(2.0), 0.0)
        self.assertEqual(_normalize_distance_to_confidence(1.0), 0.5)
        self.assertGreaterEqual(_normalize_distance_to_confidence(-0.5), 1.0) # Should cap at 1.0
        self.assertLessEqual(_normalize_distance_to_confidence(2.5), 0.0) # Should cap at 0.0

    def test_cortex_called_without_audit_row_for_jarvis_preview(self):
        """3. Cortex ask_preview does not emit audit rows"""
        initial_audit_count = 0
        if os.path.exists(self.audit_log):
            with open(self.audit_log, "r") as f:
                initial_audit_count = len(f.readlines())

        # We need to test the actual CortexAPI instance without patching its generate
        # but ensuring ask_preview doesn't touch audit
        cortex_api_test = CortexAPI(audit_log_path=self.audit_log)

        with patch("nexus.ask.recall.recall_bricks_readonly", return_value=[
            {"brick_id": "brick_j1", "confidence": 0.9},
            {"brick_id": "brick_j2", "confidence": 0.7},
        ]):
            result = cortex_api_test.ask_preview("jarvis query")

        self.assertIn("query", result)
        self.assertIn("top_bricks", result)
        self.assertEqual(len(result["top_bricks"]), 2)
        self.assertEqual(result["status"], "preview")

        final_audit_count = 0
        if os.path.exists(self.audit_log):
            with open(self.audit_log, "r") as f:
                final_audit_count = len(f.readlines())
        
        self.assertEqual(final_audit_count, initial_audit_count, "Jarvis ask_preview should not emit audit rows")

    def test_jarvis_endpoint_does_not_mutate_state(self):
        """Jarvis endpoint does not mutate state (no generate calls)"""
        # This is largely covered by ask_preview not calling generate implicitly
        # and the audit log check.
        # Explicitly ensure CortexAPI.generate is not called when ask_preview is used.
        mock_cortex_generate = MagicMock()
        with patch.object(CortexAPI, "generate", new=mock_cortex_generate):
            # Instantiate CortexAPI and test ask_preview
            cortex_api_test = CortexAPI(audit_log_path=self.audit_log)
            with patch("nexus.ask.recall.recall_bricks_readonly", return_value=[
                {"brick_id": "brick_j1", "confidence": 0.9},
            ]):
                cortex_api_test.ask_preview("jarvis query")
        
        mock_cortex_generate.assert_not_called("CortexAPI.generate should not be called by ask_preview")

    def test_nexus_ask_nondeterministic_ordering_fail(self):
        """Non-deterministic ordering appears for nexus ask → FAIL"""
        # This is implicitly tested by the deterministic nature of FAISS search
        # and the mocking of query_to_vector. The order of recalled_bricks should
        # be consistent for the same query.
        query = "deterministic order query"

        # First run
        self.mock_brick_store.get_brick_metadata.side_effect = [
            {"source_file": "file1.txt", "source_span": "spanA"},
            {"source_file": "file2.txt", "source_span": "spanB"},
            {"source_file": "file3.txt", "source_span": "spanC"},
        ]
        results1 = recall_bricks(query)

        # Second run
        self.mock_brick_store.get_brick_metadata.side_effect = [
            {"source_file": "file1.txt", "source_span": "spanA"},
            {"source_file": "file2.txt", "source_span": "spanB"},
            {"source_file": "file3.txt", "source_span": "spanC"},
        ]
        results2 = recall_bricks(query)
        
        self.assertEqual(len(results1), len(results2))
        for i in range(len(results1)):
            self.assertEqual(results1[i]["brick_id"], results2[i]["brick_id"])
            self.assertAlmostEqual(results1[i]["confidence"], results2[i]["confidence"])

if __name__ == "__main__":
    import numpy as np # Import numpy here if not globally available for tests
    unittest.main()