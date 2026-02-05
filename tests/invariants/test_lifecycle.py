import unittest
import os
import sys
# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from nexus.graph.manager import GraphManager
from nexus.graph.schema import Intent, Edge, EdgeType, IntentLifecycle, ScopeNode

class TestLifecycle(unittest.TestCase):
    def setUp(self):
        self.manager = GraphManager(":memory:")
        self.intent = Intent(statement="Test")
        self.manager.add_intent(self.intent)

    def test_monotonicity(self):
        # LOOSE -> FORMING (OK)
        self.manager.promote_intent(self.intent.id, IntentLifecycle.FORMING)
        
        # FORMING -> LOOSE (Fail)
        with self.assertRaises(ValueError):
            self.manager.promote_intent(self.intent.id, IntentLifecycle.LOOSE)

    def test_frozen_requires_scope(self):
        # Promote to FORMING first
        self.manager.promote_intent(self.intent.id, IntentLifecycle.FORMING)
        
        # Try FROZEN (Fail - No Scope)
        with self.assertRaisesRegex(ValueError, "without APPLIES_TO"):
            self.manager.promote_intent(self.intent.id, IntentLifecycle.FROZEN)
            
        # Add Scope
        scope = ScopeNode(name="TEST")
        self.manager.add_scope(scope)
        edge = Edge(self.intent.id, scope.id, EdgeType.APPLIES_TO)
        self.manager.add_typed_edge(edge)
        
        # Try FROZEN (OK)
        self.manager.promote_intent(self.intent.id, IntentLifecycle.FROZEN)

    def test_overrides_requires_frozen_source(self):
        # Intent A (LOOSE) tries to override Intent B
        target = Intent(statement="Target")
        self.manager.add_intent(target)
        
        edge = Edge(self.intent.id, target.id, EdgeType.OVERRIDES)
        
        # Fail
        with self.assertRaisesRegex(ValueError, "non-FROZEN"):
            self.manager.add_typed_edge(edge)
            
        # Freeze Source (Needs Scope first)
        self.manager.promote_intent(self.intent.id, IntentLifecycle.FORMING)
        scope = ScopeNode(name="TEST")
        self.manager.add_scope(scope)
        self.manager.add_typed_edge(Edge(self.intent.id, scope.id, EdgeType.APPLIES_TO))
        self.manager.promote_intent(self.intent.id, IntentLifecycle.FROZEN)
        
        # Retry Override (OK)
        self.manager.add_typed_edge(edge)

if __name__ == "__main__":
    unittest.main()
