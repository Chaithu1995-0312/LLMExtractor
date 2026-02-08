# Rules and Invariants

## 1. Zero-Trust Ingestion
**Rule:** No fact enters the system unless it can be traced byte-for-byte to a source log.
*   **Invariant:** `hash(extracted_text) == hash(source_text[start:end])`
*   **Enforcement:** `NexusCompiler._materialize_brick` performs this check. If it fails, the brick is silently discarded (Hard Reject).
*   **Risk:** Hallucinated pointers from LLMs are common; this invariant is the primary defense against data corruption.

## 2. Monotonic Truth (Lifecycle Governance)
**Rule:** Knowledge states can only progress forward, never backward.
*   **State Machine:**
    *   `LOOSE` (Default/Improvise)
    *   `FORMING` (Draft)
    *   `FROZEN` (Locked/Truth)
    *   `SUPERSEDED` (Obsolete - by another FROZEN node)
    *   `KILLED` (Rejected)
*   **Invariant:** A `FROZEN` node can NEVER be modified. It can only be `SUPERSEDED` by a new node.
*   **Enforcement:** `GraphManager.promote_node_to_frozen` and `GraphManager.promote_intent`.
*   **Constraint:** `supersede_node` requires both Old and New nodes to be `FROZEN`.

## 3. Budget-Aware Cognition
**Rule:** Cognitive operations must respect cost tiers.
*   **Tier L1 (Pulse):** $0.00 (Local/Ollama). Used for logs/status.
*   **Tier L2 (Voice):** ~$0.01 (Claude 3.5 Sonnet). Used for Q&A.
*   **Tier L3 (Sage):** ~$0.15 (o1/GPT-4o). Used for Deep Synthesis.
*   **Enforcement:** `JarvisGateway` logic and `proxy_config.yaml` limits (429 Daily Budget Exceeded).
*   **Invariant:** `CortexAPI.ask_preview` MUST be Read-Only and use Tier L2 or lower.

## 4. Graph Integrity
**Rule:** The Graph must remain consistent and acyclic (where applicable).
*   **Invariant:** No cycles allowed in `DEPENDS_ON` edges.
*   **Enforcement:** `validation.validate_no_cycles` runs periodically.
*   **Invariant:** A `FROZEN` Intent must be anchored to at least one Scope (`APPLIES_TO`).
*   **Enforcement:** `GraphManager.promote_intent` checks for scope edge before freezing.

## 5. Audit Traceability
**Rule:** Every high-cost or high-stakes action must be logged.
*   **Invariant:** All `FROZEN`, `KILLED`, or `SUPERSEDED` transitions must have an `actor` and `reason`.
*   **Invariant:** All L2/L3 cognitive calls must log token usage and cost.
*   **Enforcement:** `GraphManager._log_audit_event` and `CortexAPI._audit_trace`.
