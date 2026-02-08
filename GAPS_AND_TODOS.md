# GAPS_AND_TODOS.md

## 🔴 Missing Core Features

### 1. Automated Self-Healing (`services/cortex/api.py`)
- **Method**: `trigger_self_healing`
- **Gap**: Currently declared but not implemented.
- **Responsibility**: Identify and resolve logical contradictions in the graph using LLM reasoning.
- **Status**: 🔴

### 2. Multi-Hop Relationship Discovery (`src/nexus/cognition/synthesizer.py`)
- **Method**: `run_deep_synthesis` (IMPLIED)
- **Gap**: Current synthesis only looks at immediate neighbors.
- **Responsibility**: Discover transitive relationships across the entire graph.
- **Status**: 🧪 (Conceptual)

### 3. Agentic Conflict Resolution (`src/nexus/graph/validation.py`)
- **Method**: `resolve_conflicts_agentic` (IMPLIED)
- **Gap**: Validation detects issues but doesn't resolve them.
- **Responsibility**: Spawn an LLM agent to adjudicate between conflicting intents based on source authority.
- **Status**: 🔴

## 🟡 Partial Implementations

### 1. Sentiment-Aware Synthesis (`src/nexus/cognition/dspy_modules.py`)
- **Method**: `analyze_sentiment` in `RelationshipSynthesizer`
- **Gap**: Method exists but results aren't yet factored into edge weightings.
- **Status**: 🟡

### 2. Live Cognitive Visualization (`ui/jarvis/src/components/CortexVisualizer.tsx`)
- **Gap**: Component is a placeholder/mock.
- **Responsibility**: Show real-time "thoughts" and retrieval weights during query processing.
- **Status**: 🧪

### 3. Hierarchical Recall (`src/nexus/ask/recall.py`)
- **Gap**: `get_scope_hierarchy` is implemented but vector search doesn't yet fully exploit the hierarchy (it uses a flat list of allowed scopes).
- **Status**: 🟡

## 🛠️ Technical Debt & Cleanup

- **TODO**: Transition `src/nexus/graph/manager.py` from raw SQLite queries to a structured Query Builder to reduce SQL injection risks.
- **TODO**: Implement real-time WebSocket pulsing for `sync_bricks_task` so the UI reflects ingestion progress.
- **TODO**: Add thorough unit tests for `supersede_node` edge inheritance logic.
- **TODO**: Replace `print` statements in `NexusCompiler` with structured logging.
- **TODO**: Optimize `project_intent` spatial layout algorithm for graphs with >1000 nodes (current O(N^2) complexity).
