import unittest
import os
import sys
# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from nexus.graph.schema import Intent, IntentLifecycle, IntentType, ScopeNode, Edge, EdgeType
from nexus.graph.projection import project_intent, WallCell

class TestGraphProjection(unittest.TestCase):
    def test_priority_ladder(self):
        # 1. KILLED takes precedence over everything
        i = Intent(lifecycle=IntentLifecycle.KILLED, intent_type=IntentType.STRUCTURE)
        self.assertEqual(project_intent(i, [], {}, {}), WallCell.HISTORICAL)

        # 2. Conflict takes precedence over Frozen/Structure
        i = Intent(lifecycle=IntentLifecycle.FROZEN, intent_type=IntentType.STRUCTURE)
        conflict_edge = Edge(i.id, "x", EdgeType.CONFLICTS_WITH)
        self.assertEqual(project_intent(i, [conflict_edge], {}, {}), WallCell.CONFLICTS)
        
        # 3. Frozen Global Rule
        i = Intent(lifecycle=IntentLifecycle.FROZEN, intent_type=IntentType.RULE)
        scope = ScopeNode(id="s1", name="GLOBAL")
        edges = [Edge(i.id, "s1", EdgeType.APPLIES_TO)]
        self.assertEqual(project_intent(i, edges, {"s1": scope}, {}), WallCell.FROZEN_RULES)
        
        # 4. Frozen Structure
        i = Intent(lifecycle=IntentLifecycle.FROZEN, intent_type=IntentType.STRUCTURE)
        self.assertEqual(project_intent(i, [], {}, {}), WallCell.ACTIVE_ARCHITECTURE)
        
        # 5. Forming
        i = Intent(lifecycle=IntentLifecycle.FORMING)
        self.assertEqual(project_intent(i, [], {}, {}), WallCell.FORMING_PLANS)

if __name__ == "__main__":
    unittest.main()
