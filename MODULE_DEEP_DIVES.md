# Module Deep Dives

## 1. Nexus Graph Core (`src/nexus/graph`)

### Data Model (`schema.py`)
The graph is built on four primary node types and strict edge typing:

- **Intents**: Represents assertions or knowledge units.
    - Fields: `statement`, `lifecycle` (Enum), `intent_type` (Enum).
    - Invariant: Must track `lifecycle` state.
- **Scopes**: Represents context or domains (e.g., "Architecture").
    - Fields: `name`, `description`.
- **Sources**: Represents raw provenance.
    - Fields: `content`, `origin_file`, `origin_span`.
- **Edges**: Directed relationships.
    - Types: `DERIVED_FROM`, `APPLIES_TO`, `OVERRIDES`, `CONFLICTS_WITH`, `REFINES`, `DEPENDS_ON`.

### Manager Logic (`manager.py`)
The `GraphManager` acts as the persistence and logic layer over SQLite.

- **Persistence**: Flat tables `nodes` (JSON blob) and `edges` (JSON blob).
- **Lifecycle Management**: `promote_intent` enforces monotonic transitions:
    - `LOOSE` $\rightarrow$ `FORMING` $\rightarrow$ `FROZEN` $\rightarrow$ `SUPERSEDED` / `KILLED`.
    - **Critical Invariant**: A generic `FROZEN` intent MUST have an `APPLIES_TO` edge pointing to a `ScopeNode`.
- **Edge Logic**: `add_typed_edge` enforces write-time invariants (e.g., `OVERRIDES` requires source to be `FROZEN`).

## 2. Cognition Layer (`src/nexus/cognition`)

### DSPy Integration (`dspy_modules.py`)
Uses the DSPy framework to programmatically extract structured data from unstructured text.

- **Fact Extraction**:
    - Signature: `context` $\rightarrow$ `facts` (List of atomic statements).
    - Module: `dspy.ChainOfThought(FactSignature)`.
- **Diagram Extraction**:
    - Signature: `context` $\rightarrow$ `latex_formulas`, `mermaid_diagrams`.
    - Module: `dspy.ChainOfThought(DiagramSignature)`.

### Assembler (`assembler.py`)
Orchestrates the raw-to-structured pipeline:
1.  Receives a `topic` or query.
2.  Recalls relevant Bricks via Vector Store.
3.  Passes Bricks to `CognitiveExtractor`.
4.  Projects extracted Facts into `Intent` candidates (`LOOSE` state).

## 3. Cortex Service (`services/cortex`)

### API Architecture (`server.py`)
Flask-based wrapper exposing internal Managers to the outer world (UI/MCP).

- **Endpoints**:
    - `GET /jarvis/graph-index`: Dumps full graph state for visualization.
    - `POST /jarvis/anchor`: Handles "Promote" (Anchor) and "Reject" actions from UI.
    - `GET /jarvis/brick-meta`: Retrieves raw text context for a Brick ID.
    - `POST /cognition/assemble`: Triggers on-demand topic assembly.
- **Error Handling**: Standard HTTP codes (400 for bad input, 404 for missing resources, 500 for internal errors).
- **Dependency Injection**: Instantiates `GraphManager` and `LocalVectorIndex` per request (or singleton via module scope).

## 4. Ingestion Pipeline (`src/nexus/sync`)

### History Ingestion (`ingest_history.py`)
- **Source**: `conversations.json` (Exported chat logs).
- **Process**:
    1.  Load JSON tree.
    2.  Traverse messages.
    3.  `Extractor` splits content by double newlines (`\n\n`).
    4.  Generate stable IDs (UUID or Hash).
    5.  Embed text via `Embedder`.
    6.  Upsert to `LocalVectorIndex`.
