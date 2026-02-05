# Rules and Invariants

## Core Directives

### 1. The Mode-1 Invariant (No Summary Retrieval)
-   **Rule**: Retrieval must never serve summarized content or embeddings directly to the generation model without reloading the original raw source.
-   **Enforcement**: `CortexAPI._reload_source_text` explicitly loads content from `BrickStore`. If this fails (return empty), the `generate` call is aborted with `status: blocked`.
-   **Rationale**: Summaries drift; raw data is ground truth.

### 2. Immutable History
-   **Rule**: Ingested conversation history is immutable. It is never modified or deleted by the system.
-   **Enforcement**: `src/nexus/sync` only appends/creates new bricks. Existing bricks are identified by SHA256 content hash and skipped if already present (idempotency).

### 3. Monotonic Knowledge Growth
-   **Rule**: New knowledge does not delete old knowledge; it supersedes it.
-   **Enforcement**: `GraphManager` uses `OVERRIDES` edges to link conflicting Intents.
-   **Lifecycle**:
    -   `LOOSE`: Just observed.
    -   `FORMING`: Confirmed by multiple sources or high confidence.
    -   `FROZEN`: System invariant (requires explicit override).
    -   `SUPERSEDED`: Replaced by a newer intent.
    -   `KILLED`: Explicitly rejected.

### 4. Zero-Hallucination Assembly
-   **Rule**: Topic assembly must only use facts explicitly present in the source bricks.
-   **Enforcement**: DSPy signatures (`CognitiveExtractor`) are designed to extract, not invent. The system relies on the LLM's adherence to the prompt context. (Note: This is probabilistic, not deterministic code-level enforcement).

## Data Integrity

### Brick Immutability
-   **ID Generation**: `sha256(source_file + index + content)`.
-   **Constraint**: If the source file changes, new bricks are generated. Old bricks become orphaned in the index but remain in the store (unless a purge script is run, which is not currently implemented).

### Graph Integrity
-   **Schema**: Nodes and Edges must conform to types defined in `src/nexus/graph/schema.py`.
-   **Validation**: `src/nexus/graph/validation.py` (referenced) likely runs periodic checks to ensure no dangling edges or invalid lifecycle states.

## Security & Audit
-   **Audit Trace**: Every `generate` call using Nexus memory must be logged to `phase3_audit_trace.jsonl`.
-   **Fields**: `user_id`, `agent_id`, `brick_ids_used`, `model`, `token_cost`.
-   **Scope Access**: `recall_bricks` boosts priority for non-global scopes but does not strictly *deny* access to global scopes (currently). Hard ACLs are not yet visible.
