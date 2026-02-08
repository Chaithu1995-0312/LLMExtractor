from enum import Enum
from typing import List, Dict
from nexus.graph.schema import Intent, Edge, EdgeType, IntentLifecycle, IntentType, ScopeNode

class WallCell(Enum):
    FROZEN_RULES = 1
    FORMING_PLANS = 2
    OPEN_QUESTIONS = 3
    ACTIVE_ARCHITECTURE = 4
    CURRENT_TRUTH = 5
    CONFLICTS = 6
    HISTORICAL = 7
    STALE = 8
    SUGGESTIONS = 9

def get_intent_edges(intent_id: str, edges: List[Edge]) -> Dict[str, List[Edge]]:
    """Helper to get edges connected to an intent."""
    connected = {
        "outgoing": [e for e in edges if e.source_id == intent_id],
        "incoming": [e for e in edges if e.target_id == intent_id]
    }
    return connected

def is_global_scope(intent_id: str, edges: List[Edge], scope_nodes: Dict[str, ScopeNode]) -> bool:
    """Check if intent applies to GLOBAL scope."""
    outgoing = [e for e in edges if e.source_id == intent_id and e.edge_type == EdgeType.APPLIES_TO]
    for edge in outgoing:
        scope = scope_nodes.get(edge.target_id)
        if scope and scope.name.upper() == "GLOBAL":
            return True
    return False

def has_conflict(intent_id: str, edges: List[Edge]) -> bool:
    """
    Check if intent has active conflicts.
    Logic includes:
    1. Explicit CONFLICTS_WITH edges.
    2. Structural conflicts (e.g., both OVERRIDES and being OVERRIDDEN by different active nodes).
    3. Multiple active intents derived from the same source brick without resolution.
    """
    # 1. Explicit conflict edges
    for edge in edges:
        if edge.edge_type == EdgeType.CONFLICTS_WITH:
            if edge.source_id == intent_id or edge.target_id == intent_id:
                return True
                
    # 2. Structural: Check for circular or competing overrides
    outgoing_overrides = [e for e in edges if e.source_id == intent_id and e.edge_type == EdgeType.OVERRIDES]
    incoming_overrides = [e for e in edges if e.target_id == intent_id and e.edge_type == EdgeType.OVERRIDES]
    
    if outgoing_overrides and incoming_overrides:
        # Node is trying to override something while being overridden itself (ambiguous truth)
        return True
        
    # 3. Source-level competition: Are there other intents derived from the same bricks?
    source_brick_ids = [e.target_id for e in edges if e.source_id == intent_id and e.edge_type == EdgeType.DERIVED_FROM]
    for brick_id in source_brick_ids:
        # Find other intents sharing this brick
        other_intents = [e.source_id for e in edges if e.target_id == brick_id and e.edge_type == EdgeType.DERIVED_FROM and e.source_id != intent_id]
        if other_intents:
            # Check if these competing intents are active
            # (Note: This is a limited check as we don't have the full intent lifecycle list here, 
            # but we can flag based on shared provenance alone for manual triage).
            return True
            
    return False

def is_from_agent(intent_id: str, edges: List[Edge], sources: Dict[str, any]) -> bool:
    """Check if intent is derived from an Agent source."""
    outgoing = [e for e in edges if e.source_id == intent_id and e.edge_type == EdgeType.DERIVED_FROM]
    for edge in outgoing:
        source = sources.get(edge.target_id)
        # heuristic: check metadata or content for 'Agent' role
        if source and source.metadata.get("role") == "assistant":
            return True
    return False

def project_intent(
    intent: Intent, 
    edges: List[Edge], 
    scope_nodes: Dict[str, ScopeNode],
    sources: Dict[str, any]
) -> WallCell:
    """
    Project an Intent into the 3x3 Grid based on deterministic logic.
    """
    
    # 1. Historical / Killed
    if intent.lifecycle in [IntentLifecycle.KILLED, IntentLifecycle.SUPERSEDED]:
        return WallCell.HISTORICAL
        
    # 2. Conflicts
    if has_conflict(intent.id, edges):
        return WallCell.CONFLICTS
        
    # 3. Stale
    # Assuming explicit metadata flag or some time-based logic. 
    # For now, relying on metadata.
    if intent.metadata.get("is_stale", False):
        return WallCell.STALE
        
    # 4. Forming
    if intent.lifecycle == IntentLifecycle.FORMING:
        return WallCell.FORMING_PLANS
        
    # 5. Frozen / Active (Frozen implies Active in this context if not Stale/Killed)
    if intent.lifecycle == IntentLifecycle.FROZEN:
        if is_global_scope(intent.id, edges, scope_nodes):
            return WallCell.FROZEN_RULES
        elif intent.intent_type == IntentType.STRUCTURE:
            return WallCell.ACTIVE_ARCHITECTURE
        elif intent.intent_type == IntentType.FORMULA:
            return WallCell.FROZEN_RULES
        else:
            return WallCell.CURRENT_TRUTH
            
    # 6. Suggestions (Agent derived)
    # Check if it's LOOSE and from Agent
    if intent.lifecycle == IntentLifecycle.LOOSE:
        if is_from_agent(intent.id, edges, sources):
            return WallCell.SUGGESTIONS
            
    # 7. Default / Loose -> Open Questions / Triage
    return WallCell.OPEN_QUESTIONS
