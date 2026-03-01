import unittest
from nexus.graph.manager import GraphManager, IntentLifecycle, EdgeType

class TestLifecycleIntegrity(unittest.TestCase):
    def setUp(self):
        self.manager = GraphManager(":memory:")

    def test_initial_state_is_loose(self):
        # Ingestion creates a brick, which is a node
        brick_id = "brick_1"
        self.manager.register_node("brick", brick_id, {"statement": "Test brick"})
        
        node_type, data = self.manager.get_node(brick_id)
        self.assertEqual(data.get("lifecycle", "loose"), "loose")

    def test_cannot_freeze_without_scope(self):
        intent_id = "intent_1"
        self.manager.register_node("intent", intent_id, {"statement": "Test intent", "lifecycle": "forming"})
        
        with self.assertRaises(ValueError):
            self.manager.promote_intent(intent_id, IntentLifecycle.FROZEN)

    def test_monotonic_lifecycle(self):
        intent_id = "intent_2"
        self.manager.register_node("intent", intent_id, {"statement": "Test intent"})
        
        # Add a scope to allow freezing
        scope_id = "scope_1"
        self.manager.register_node("scope", scope_id, {"name": "Test Scope"})
        self.manager.register_edge(("intent", intent_id), ("scope", scope_id), EdgeType.APPLIES_TO)

        # LOOSE -> FORMING
        self.manager.promote_intent(intent_id, IntentLifecycle.FORMING)
        _, data = self.manager.get_node(intent_id)
        self.assertEqual(data["lifecycle"], "forming")

        # FORMING -> FROZEN
        self.manager.promote_intent(intent_id, IntentLifecycle.FROZEN)
        _, data = self.manager.get_node(intent_id)
        self.assertEqual(data["lifecycle"], "frozen")
        
        # FROZEN -> FORMING (should fail)
        with self.assertRaises(ValueError):
            self.manager.promote_intent(intent_id, IntentLifecycle.FORMING)

if __name__ == "__main__":
    unittest.main()
