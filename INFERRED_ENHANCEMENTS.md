# Inferred Enhancements

## High-Value Strategic Upgrades

### 1. Graph-Augmented RAG (GraphRAG)
**Context**: Currently, recall is purely vector-based (`recall_bricks`).
**Proposal**:
- Use `ScopeNodes` and `Intent` links to expand the context window.
- When a Brick is recalled, traverse `DERIVED_FROM` edges to fetch related Canonical Intents.
- **Benefit**: Answers become grounded in "Frozen" knowledge rather than just raw historical chat logs.

### 2. Autonomous Consistency Agents
**Context**: Graph consistency relies on manual "Promote" actions.
**Proposal**:
- Create background agents using DSPy that:
    1.  Scan `FROZEN` intents.
    2.  Check for contradictions with new `LOOSE` intents.
    3.  Suggest `CONFLICTS_WITH` edges automatically.
- **Benefit**: Reduces human load in maintaining truth.

### 3. Active Learning Loop
**Context**: User feedback ("Reject") is stored but not used for training.
**Proposal**:
- Feed `rejected` anchors back into a fine-tuning dataset for the Embedding model or Reranker.
- **Benefit**: System learns the user's preference for "high-quality" bricks over time.

## Cognitive Pipeline Refinement (Targeted)

### 4. Specialized DSPy Architectures
**Context**: `FactSignature` is too generic for technical documentation.
**Proposal**:
- **CodeSignature**: Extract `function_name`, `arguments`, `return_type`, `invariants`.
- **DefinitionSignature**: Extract `term`, `definition`, `context`.
- **ArchitectureSignature**: Extract `component`, `responsibility`, `dependencies`.
- **Implementation**: Chain these modules conditionally based on Brick classification.

### 5. Reranking Integration
**Context**: `cross_encoder.py` exists but is disconnected from the hot path.
**Proposal**:
- **Pipeline Update**: `Recall (Vector)` $\rightarrow$ `Top-K (50)` $\rightarrow$ `Rerank (CrossEncoder)` $\rightarrow$ `Top-N (5)` $\rightarrow$ `Context`.
- **Latency**: Run Reranker on GPU or use a distilled model (e.g., `ms-marco-TinyBERT`) to keep latency < 200ms.

### 6. Hallucination Guardrails
**Context**: Extracted intents may drift from source text.
**Proposal**:
- **Citation Check Module**: A specialized LLM pass that takes `(Intent, SourceBrick)` and outputs `Score [0-1]`.
- **Rule**: If Score < 0.8, auto-reject or flag the Intent as `SUSPICIOUS`.
- **Benefit**: Ensures high-fidelity knowledge extraction.

## User Experience Enhancements

### 7. Semantic Zoom
**Context**: Graph view can become cluttered.
**Proposal**:
- Implement "Semantic Zoom" in Jarvis.
- High Level: Show only `ScopeNodes` and key `FROZEN` intents.
- Low Level: Reveal `LOOSE` intents and raw `Source` nodes.

### 8. Multi-Modal Bricks
**Context**: Current Bricks are text-only.
**Proposal**:
- Extend `schema.py` to support Image or Code Bricks (with AST analysis).
- **Benefit**: Better handling of code snippets and architectural diagrams found in chat.
