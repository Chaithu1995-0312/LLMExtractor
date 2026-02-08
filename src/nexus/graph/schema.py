from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

class IntentLifecycle(Enum):
    LOOSE = "loose"
    FORMING = "forming"
    FROZEN = "frozen"
    SUPERSEDED = "superseded"
    KILLED = "killed"

class IntentType(Enum):
    RULE = "rule"
    FACT = "fact"
    FORMULA = "formula"
    STRUCTURE = "structure"
    QUESTION = "question"
    GOAL = "goal"
    UNKNOWN = "unknown"

class EdgeType(Enum):
    DERIVED_FROM = "derived_from"     # Intent -> Source
    APPLIES_TO = "applies_to"         # Intent -> ScopeNode
    OVERRIDES = "overrides"           # Intent -> Intent
    CONFLICTS_WITH = "conflicts_with" # Intent -> Intent
    REFINES = "refines"               # Intent -> Intent
    DEPENDS_ON = "depends_on"         # Intent -> Intent
    ASSEMBLED_IN = "assembled_in"     # Topic -> Artifact or Topic -> Intent
    SUPERSEDED_BY = "superseded_by"   # Intent -> Intent (Versioning)

class AuditEventType(str, Enum):
    # --- COMPILER / INGESTION ---
    RUN_COMPILE_STARTED = "RUN_COMPILE_STARTED"
    RUN_COMPILE_COMPLETED = "RUN_COMPILE_COMPLETED"

    LLM_CALL_EXECUTED = "LLM_CALL_EXECUTED"
    LLM_CALL_SKIPPED = "LLM_CALL_SKIPPED"

    POINTERS_EXTRACTED = "POINTERS_EXTRACTED"
    BRICK_MATERIALIZED = "BRICK_MATERIALIZED"
    LLM_POINTER_MISMATCH = "LLM_POINTER_MISMATCH"
    LLM_PATH_OUT_OF_BOUNDS = "LLM_PATH_OUT_OF_BOUNDS"

    BOUNDARY_ADVANCED = "BOUNDARY_ADVANCED"

    # --- GRAPH / GOVERNANCE ---
    EDGE_CREATED = "EDGE_CREATED"
    EDGE_REJECTED = "EDGE_REJECTED"

    NODE_PROMOTED = "NODE_PROMOTED"
    NODE_FROZEN = "NODE_FROZEN"
    NODE_SUPERSEDED = "NODE_SUPERSEDED"
    NODE_KILLED = "NODE_KILLED"

    # --- PROMPT GOVERNANCE ---
    PROMPT_LOADED = "PROMPT_LOADED"
    PROMPT_VERSION_USED = "PROMPT_VERSION_USED"
    PROMPT_GOVERNANCE_VIOLATION = "PROMPT_GOVERNANCE_VIOLATION"
    PROMPT_FALLBACK_USED = "PROMPT_FALLBACK_USED"
    PROMPT_NOT_APPROVED = "PROMPT_NOT_APPROVED"

    # --- QUERY / COGNITION (FUTURE-SAFE) ---
    QUERY_RECEIVED = "QUERY_RECEIVED"
    QUERY_ROUTED = "QUERY_ROUTED"

    PULSE_EMITTED = "PULSE_EMITTED"
    SYNTHESIS_TRIGGERED = "SYNTHESIS_TRIGGERED"

class ModelTier(str, Enum):
    L1 = "L1"  # local / free
    L2 = "L2"  # standard cloud
    L3 = "L3"  # reasoning / expensive

class DecisionAction(str, Enum):
    LLM_CALL = "LLM_CALL"
    SKIPPED = "SKIPPED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    PROMOTED = "PROMOTED"
    SUPERSEDED = "SUPERSEDED"
    BLOCKED = "BLOCKED"

@dataclass
class GraphNode:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Source(GraphNode):
    content: str = ""
    origin_file: str = ""
    origin_span: Optional[List[int]] = None
    node_type: str = "source"

@dataclass
class ScopeNode(GraphNode):
    name: str = ""
    description: str = ""
    node_type: str = "scope"

@dataclass
class Intent(GraphNode):
    statement: str = ""
    lifecycle: IntentLifecycle = IntentLifecycle.LOOSE
    intent_type: IntentType = IntentType.UNKNOWN
    node_type: str = "intent"

@dataclass
class Edge:
    source_id: str
    target_id: str
    edge_type: EdgeType
    metadata: Dict[str, Any] = field(default_factory=dict)
