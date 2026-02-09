import unittest
import json
import os
from nexus.bricks.extractor import classify_brick_type
from nexus.bricks.resolver import UserTriggeredResolver

class MockGraphManager:
    def __init__(self):
        self.bricks = []
        self.marking_calls = []

    def get_loose_bricks(self, topic_id):
        return [b for b in self.bricks if b["lifecycle"] == "loose"]

    def mark_forming(self, brick_id, resolved_by, actor):
        self.marking_calls.append({
            "brick_id": brick_id,
            "resolved_by": resolved_by,
            "actor": actor
        })
        for b in self.bricks:
            if b["id"] == brick_id:
                b["lifecycle"] = "forming"

class TestQuestionResolution(unittest.TestCase):
    def test_classification(self):
        self.assertEqual(classify_brick_type("assistant", "What is Nexus?"), "query")
        self.assertEqual(classify_brick_type("assistant", "Nexus is a graph."), "answer")
        self.assertEqual(classify_brick_type("user", "Hello?"), "input")
        self.assertEqual(classify_brick_type("system", "Strict mode on."), "doctrine")

    def test_resolver_trigger(self):
        graph = MockGraphManager()
        resolver = UserTriggeredResolver(graph)
        
        self.assertTrue(resolver.is_triggered("Continue"))
        self.assertTrue(resolver.is_triggered("1. Answer one\n2. Answer two"))
        self.assertTrue(resolver.is_triggered("- Bullet point"))
        self.assertFalse(resolver.is_triggered("Just some text"))

    def test_structural_overlap(self):
        graph = MockGraphManager()
        resolver = UserTriggeredResolver(graph)
        
        q = "Which data source should Nexus prioritize?"
        a = "Nexus should prioritize the primary data source."
        self.assertTrue(resolver.is_covered(q, a)) # "prioritize" is 10 chars
        
        a2 = "I don't know."
        self.assertFalse(resolver.is_covered(q, a2))

    def test_positional_resolution(self):
        graph = MockGraphManager()
        graph.bricks = [
            {"id": "q1", "statement": "Question 1?", "lifecycle": "loose", "created_at": "2026-01-01T00:00:00Z"},
            {"id": "q2", "statement": "Question 2?", "lifecycle": "loose", "created_at": "2026-01-01T00:00:01Z"}
        ]
        resolver = UserTriggeredResolver(graph)
        
        user_msg = {
            "message_id": "ans_1",
            "content": "continue\nAnswer to first question\nAnswer to second"
        }
        
        report = resolver.resolve("test_topic", user_msg)
        
        self.assertEqual(len(report["resolved"]), 2)
        self.assertEqual(len(graph.marking_calls), 2)
        self.assertEqual(graph.marking_calls[0]["brick_id"], "q1")
        self.assertEqual(graph.marking_calls[1]["brick_id"], "q2")

    def test_positional_gate_regression(self):
        """Verify Rule B doesn't fire without 'continue'."""
        graph = MockGraphManager()
        graph.bricks = [
            {"id": "q1", "statement": "Question 1?", "lifecycle": "loose", "created_at": "1"}
        ]
        resolver = UserTriggeredResolver(graph)
        
        # Multiline text triggers resolver, but Rule B (positional) should be gated by 'continue'
        user_msg = {
            "message_id": "ans_1",
            "content": "Line one\nLine two"
        }
        
        report = resolver.resolve("test_topic", user_msg)
        self.assertEqual(len(report["resolved"]), 0) # No overlap, and no 'continue' for positional

    def test_mixed_resolution(self):
        graph = MockGraphManager()
        graph.bricks = [
            {"id": "q1", "statement": "Target data source?", "lifecycle": "loose", "created_at": "1"},
            {"id": "q2", "statement": "Auth method?", "lifecycle": "loose", "created_at": "2"}
        ]
        resolver = UserTriggeredResolver(graph)
        
        # In my code trigger is: "continue" or "\n" or "1." or "- "
        # user_msg["content"] = "The Auth method? should be OAuth2.\nAnd skip the rest."
        # positional_allowed will be FALSE here because "continue" is missing.
        user_msg = {
            "message_id": "ans_1",
            "content": "The Auth method? should be OAuth2.\nAnd skip the rest."
        }
        report = resolver.resolve("test_topic", user_msg)
        
        # q2 (idx 1) matches "Auth method?" block via overlap
        # q1 (idx 0) has NO overlap. positional_allowed=False
        # So only 1 resolved.
        self.assertEqual(len(report["resolved"]), 1)
        self.assertIn("Auth method?", report["resolved"])
        
        # Now reset state for second part
        graph.bricks = [
            {"id": "q1", "statement": "Target data source?", "lifecycle": "loose", "created_at": "1"},
            {"id": "q2", "statement": "Auth method?", "lifecycle": "loose", "created_at": "2"}
        ]
        # Now add "continue"
        user_msg["content"] = "continue\nThe Auth method? should be OAuth2.\nAnd skip the rest."
        report = resolver.resolve("test_topic", user_msg)
        # Blocks are: ["continue", "The Auth method? should be OAuth2.", "And skip the rest."] (3 blocks)
        # q1 (idx 0) -> Rule B (idx 0 < 3) -> covered
        # q2 (idx 1) -> Rule A (overlap) -> covered
        self.assertEqual(len(report["resolved"]), 2)

if __name__ == "__main__":
    unittest.main()
