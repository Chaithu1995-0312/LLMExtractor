from typing import List, Dict
from nexus.graph.manager import GraphManager
from nexus.graph.schema import IntentLifecycle, EdgeType

def validate_frozen_scope(manager: GraphManager) -> List[str]:
    """Returns list of FROZEN intent IDs missing APPLIES_TO edge."""
    intents = manager.get_all_intents()
    frozen = [i for i in intents if i.lifecycle == IntentLifecycle.FROZEN]
    violations = []
    for i in frozen:
        edges = manager.get_edges_for_node(i.id)
        has_scope = any(e.edge_type == EdgeType.APPLIES_TO and e.source_id == i.id for e in edges)
        if not has_scope:
            violations.append(i.id)
    return violations

def validate_orphans(manager: GraphManager) -> List[str]:
    """Returns list of Intent IDs without DERIVED_FROM source."""
    intents = manager.get_all_intents()
    violations = []
    for i in intents:
        edges = manager.get_edges_for_node(i.id)
        has_source = any(e.edge_type == EdgeType.DERIVED_FROM and e.source_id == i.id for e in edges)
        if not has_source:
            violations.append(i.id)
    return violations

def validate_no_cycles(manager: GraphManager) -> List[str]:
    """
    Detect cycles in OVERRIDES relationships.
    Returns list of node IDs involved in the first detected cycle.
    """
    all_intents = manager.get_all_intents()
    visited = set()
    path = []
    
    def find_cycle(node_id, current_path):
        if node_id in current_path:
            # Cycle detected
            cycle_start_idx = current_path.index(node_id)
            return current_path[cycle_start_idx:]
        
        if node_id in visited:
            return None
            
        visited.add(node_id)
        current_path.append(node_id)
        
        edges = manager.get_edges_for_node(node_id)
        # OVERRIDES relationship: node_id overrides target_id
        for edge in edges:
            if edge.edge_type == EdgeType.OVERRIDES and edge.source_id == node_id:
                cycle = find_cycle(edge.target_id, current_path)
                if cycle:
                    return cycle
                    
        current_path.pop()
        return None

    for intent in all_intents:
        if intent.id not in visited:
            cycle = find_cycle(intent.id, [])
            if cycle:
                return cycle
    return []

def run_full_validation(db_path: str = None) -> bool:
    manager = GraphManager(db_path)
    print("Running Graph Validation...")
    
    cycles = validate_no_cycles(manager)
    if cycles:
        print(f"❌ Cycle detected in OVERRIDES: {' -> '.join(cycles)} -> {cycles[0]}")
    else:
        print("✅ No cycles in OVERRIDES.")

    orphans = validate_orphans(manager)
    if orphans:
        print(f"❌ Found {len(orphans)} orphaned intents.")
    else:
        print("✅ No orphaned intents.")
        
    scope_violations = validate_frozen_scope(manager)
    if scope_violations:
        print(f"❌ Found {len(scope_violations)} FROZEN intents without scope.")
    else:
        print("✅ All FROZEN intents have scope.")
        
    return len(orphans) == 0 and len(scope_violations) == 0

if __name__ == "__main__":
    import sys
    success = run_full_validation()
    sys.exit(0 if success else 1)
