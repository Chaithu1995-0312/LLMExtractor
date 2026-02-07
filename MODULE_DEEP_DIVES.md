# MODULE_DEEP_DIVES

## 1. Cognition Engine: `Assembler`

### 1.1 Overview
The `Assembler` (`src/nexus/cognition/assembler.py`) is the engine responsible for synthesizing scattered "Bricks" into coherent "Topics". It bridges the gap between raw vector retrieval and structured knowledge graph updates.

### 1.2 The `assemble_topic` Pipeline

1. **Recall Phase (Read-Only)**
   - Inputs: `topic_query` (string)
   - Action: Calls `recall_bricks_readonly(topic_query, k=15)`.
   - Output: List of candidate bricks with similarity scores.
   - *Note:* If no bricks are found, it creates an empty "NO_RECALL_MATCHES" artifact.

2. **Expansion & Deduplication Phase**
   - Goal: Contextualize bricks.
   - Action: Loads full conversation trees for each brick. Deduplicates multiple bricks coming from the same conversation to avoid redundancy.
   - Result: `unique_docs` map containing full context window.

3. **Cognitive Extraction Phase**
   - Tool: `CognitiveExtractor` (DSPy).
   - Inputs: Aggregated text from all unique docs.
   - Action: 
     - Extracts **Atomic Facts** (`FactSignature`).
     - Extracts **Visuals** (`DiagramSignature`: Latex, Mermaid).
   - *Error Handling:* Wraps DSPy call in try-except; defaults to empty lists on failure.

4. **Persistence Phase**
   - Action: Saves the full `artifact_payload` (provenance, raw excerpts, extracted facts) to disk (`output/nexus/artifacts/`).
   - Mechanism: Content-Addressable Storage (SHA256 hash of payload).

5. **Graph Linkage & Monotonic Conflict Resolution**
   - **Nodes:**
     - Creates `Topic` node (merged by slug).
     - Creates `Artifact` node (immutable snapshot).
   - **Edges:**
     - `Topic` -> `ASSEMBLED_IN` -> `Artifact`.
     - `Artifact` -> `DERIVED_FROM` -> `Brick`.
   - **Conflict Logic:**
     - Iterates over extracted facts.
     - Compares against existing intents for the topic using `CrossEncoderReranker`.
     - **Rule:** If new fact is highly similar (>0.85) to an existing `FROZEN` intent, the new fact is **Overridden** (anchor wins).
     - **Rule:** If new fact is highly similar to an existing `FORMING` intent, the new fact **Supersedes** it (newest forming wins).

## 2. Graph Governance: `GraphManager`

### 2.1 Overview
The `GraphManager` (`src/nexus/graph/manager.py`) is the guardian of the Knowledge Graph. It ensures data integrity, enforces lifecycle transitions, and handles persistence to SQLite.

### 2.2 Lifecycle State Machine

The system enforces a strict lifecycle for `Intent` nodes:

- **LOOSE:** Initial state. A raw idea or fact extracted by AI. Low confidence.
- **FORMING:** Promoted by user or high-confidence AI aggregation. Gaining structure.
- **FROZEN:** Authoritative. Immutable. Can only be superseded, never changed.
- **KILLED:** Explicitly rejected. Dead end.
- **SUPERSEDED:** Historic. Replaced by a newer FROZEN node.

### 2.3 Key Operations

#### `promote_node_to_frozen`
- **Pre-condition:** Node must be `FORMING`.
- **Action:** Sets lifecycle to `FROZEN`. records `promoted_at`, `promoted_by`.
- **Side Effect:** Logs audit event `NODE_FROZEN`.

#### `supersede_node`
- **Pre-condition:** Both Old and New nodes must be `FROZEN`.
- **Action:** 
  - Creates `SUPERSEDED_BY` edge from Old to New.
  - Updates metadata on both nodes.
- **Invariant:** A node cannot supersede itself.

#### `kill_node`
- **Pre-condition:** None (can kill from any state, unless already killed).
- **Action:** Sets lifecycle to `KILLED`.
- **Note:** This is a soft delete; data remains for audit trails.
