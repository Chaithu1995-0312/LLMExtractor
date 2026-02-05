import unittest
import os
import sys
# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from nexus.graph.manager import GraphManager
from nexus.graph.schema import Intent, Source, Edge, EdgeType, IntentLifecycle, IntentType
from nexus.graph.projection import project_intent, WallCell

class TestGraphIntegrity(unittest.TestCase):
    def setUp(self):
        # Use in-memory DB for testing
        self.manager = GraphManager(":memory:")

    def test_no_orphaned_intents(self):
        """Invariant: Every Intent must have a DERIVED_FROM edge."""
        # Create Source
        source = Source(content="Test source")
        self.manager.add_source(source)
        
        # Create Intent linked to Source
        intent = Intent(statement="Test intent")
        self.manager.add_intent(intent)
        edge = Edge(intent.id, source.id, EdgeType.DERIVED_FROM)
        self.manager.add_typed_edge(edge)
        
        # Create Orphan Intent
        orphan = Intent(statement="Orphan")
        self.manager.add_intent(orphan)
        
        # Check
        intents = self.manager.get_all_intents()
        edges = self.manager.get_all_edges()
        
        linked_intents = {e.source_id for e in edges if e.edge_type == EdgeType.DERIVED_FROM}
        
        orphans = [i for i in intents if i.id not in linked_intents]
        
        # Expect 1 orphan
        self.assertEqual(len(orphans), 1)
        self.assertEqual(orphans[0].id, orphan.id)
        
        # Ideally, we assert that production data has 0 orphans.
        # But this test validates the *check* logic.

    def test_projection_completeness(self):
        """Invariant: project_intent must return a valid WallCell for all lifecycle states."""
        
        # Mock data
        edges = []
        scope_nodes = {}
        sources = {}
        
        # Test KILLED -> HISTORICAL (7)
        i1 = Intent(lifecycle=IntentLifecycle.KILLED)
        self.assertEqual(project_intent(i1, edges, scope_nodes, sources), WallCell.HISTORICAL)
        
        # Test FORMING -> FORMING_PLANS (2)
        i2 = Intent(lifecycle=IntentLifecycle.FORMING)
        self.assertEqual(project_intent(i2, edges, scope_nodes, sources), WallCell.FORMING_PLANS)
        
        # Test FROZEN + STRUCTURE -> ACTIVE_ARCHITECTURE (4)
        i3 = Intent(lifecycle=IntentLifecycle.FROZEN, intent_type=IntentType.STRUCTURE)
        self.assertEqual(project_intent(i3, edges, scope_nodes, sources), WallCell.ACTIVE_ARCHITECTURE)
        
        # Test LOOSE (Default) -> OPEN_QUESTIONS (3)
        i4 = Intent(lifecycle=IntentLifecycle.LOOSE)
        self.assertEqual(project_intent(i4, edges, scope_nodes, sources), WallCell.OPEN_QUESTIONS)

    def test_conflict_detection(self):
        """Invariant: Conflict edges push Intent to Wall 6."""
        i = Intent(lifecycle=IntentLifecycle.FROZEN)
        
        # Add conflict edge
        conflict_edge = Edge(i.id, "other_id", EdgeType.CONFLICTS_WITH)
        edges = [conflict_edge]
        
        self.assertEqual(project_intent(i, edges, {}, {}), WallCell.CONFLICTS)

if __name__ == "__main__":
    unittest.main()
