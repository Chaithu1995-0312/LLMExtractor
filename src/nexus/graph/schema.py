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
