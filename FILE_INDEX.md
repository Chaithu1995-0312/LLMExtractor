# FILE_INDEX

## 1. Backend (`src/nexus`)

### 1.1 `src/nexus/cognition/assembler.py`
**Responsibility:** Orchestrates the transformation of recalled bricks into structured topic artifacts.
- `assemble_topic(topic_query: str) -> str`: Main pipeline function.
- `_calculate_content_hash(content: Any) -> str`: Generates SHA256 hashes for content addressing.
- `_load_tree_file(path: str) -> Dict`: Helper to load conversation trees.
- `_get_slug(text: str) -> str`: Utility for filename sanitization.

### 1.2 `src/nexus/cognition/dspy_modules.py`
**Responsibility:** Defines DSPy signatures and modules for LLM-based extraction.
- `CognitiveExtractor`: Main module wrapping `FactSignature` and `DiagramSignature`.
- `CognitiveExtractor.forward(context: str) -> dspy.Prediction`: Executes the extraction pipeline.
- `FactSignature`: DSPy signature for extracting atomic facts.
- `DiagramSignature`: DSPy signature for extracting Latex and Mermaid code.

### 1.3 `src/nexus/graph/manager.py`
**Responsibility:** Manages SQLite interaction for the Knowledge Graph.
- `GraphManager.__init__(db_path: str)`: Initializes DB connection.
- `GraphManager.register_node(node_type, node_id, attrs, merge)`: Upsert logic for nodes.
- `GraphManager.register_edge(src, dst, edge_type, attrs)`: Upsert logic for edges.
- `GraphManager.get_intents_by_topic(topic_node_id)`: Retrieval query.
- `GraphManager.promote_node_to_frozen(node_id, promote_bricks, actor)`: Lifecycle transition `FORMING` -> `FROZEN`.
- `GraphManager.kill_node(node_id, reason, actor)`: Lifecycle transition -> `KILLED`.
- `GraphManager.supersede_node(old_node_id, new_node_id, reason, actor)`: Replaces a frozen node.
- `GraphManager._log_audit_event(event_type, payload)`: Audit logging.

### 1.4 `src/nexus/graph/schema.py`
**Responsibility:** Data models and enums.
- `IntentLifecycle` (Enum): `LOOSE`, `FORMING`, `FROZEN`, `SUPERSEDED`, `KILLED`.
- `EdgeType` (Enum): Defines relationships like `ASSEMBLED_IN`, `OVERRIDES`, `SUPERSEDED_BY`.
- `Intent` (Dataclass): Data structure for Intent nodes.
- `Edge` (Dataclass): Data structure for Edges.

### 1.5 `src/nexus/config.py`
**Responsibility:** Global configuration.
- `PACKAGE_ROOT`, `REPO_ROOT`, `DATA_DIR`: Path constants.

### 1.6 `src/nexus/ask/recall.py`
**Responsibility:** Semantic search interface.
- `recall_bricks_readonly(query, k)`: Retrieves relevant bricks from vector store.
- `get_recall_brick_metadata(brick_id)`: Fetches metadata for a specific brick.

## 2. Service (`services/cortex`)

### 2.1 `services/cortex/server.py`
**Responsibility:** Flask API server.
- `jarvis_graph_index()`: `GET /jarvis/graph-index` - Returns full graph for visualization.
- `jarvis_node_promote()`: `POST /jarvis/node/promote` - Promotes a node.
- `jarvis_node_kill()`: `POST /jarvis/node/kill` - Kills a node.
- `jarvis_node_supersede()`: `POST /jarvis/node/supersede` - Supersedes a node.
- `cognition_assemble()`: `POST /cognition/assemble` - Triggers topic assembly.
- `jarvis_brick_meta()`: `GET /jarvis/brick-meta` - Gets brick content.

## 3. Frontend (`ui/jarvis/src`)

### 3.1 `components/CortexVisualizer.tsx`
**Responsibility:** D3.js Graph Visualization.
- `CortexVisualizer`: React component rendering the graph. Handles D3 force simulation and drag events.

### 3.2 `components/ControlStrip.tsx`
**Responsibility:** User actions toolbar.
- `ControlStrip`: React component rendering Promote/Kill buttons based on lifecycle state.

### 3.3 `components/NexusNode.tsx`
**Responsibility:** Detailed node view.
- `NexusNode`: React component displaying node details (title, summary, confidence) with lifecycle-specific styling.
