# RULES_AND_INVARIANTS.md

## 1. Structural Invariants

### Graph Integrity
- **No Cycles**: The graph must remain a Directed Acyclic Graph (DAG) for `DEPENDS_ON` and `SUPERSEDES` edge types. Checked by `GraphManager._check_for_cycle`.
- **Atomic Promotion**: A Brick can only be promoted to an Intent node once. Fingerprint-based deduplication is enforced at the `SyncDatabase` and `GraphManager` levels.
- **Node Immutability**: Once a node is marked as `FROZEN`, its core semantic attributes (text, type) cannot be modified. Only metadata and edges can be updated.

### Versioning
- **Supersession Lineage**: When Node B supersedes Node A, Node A's status must transition to `SUPERSEDED`. Node B must inherit relevant edges or maintain a pointer to Node A.

## 2. Process Rules

### Ingestion Flow
1. **Extraction**: Must use the `NexusCompiler` to generate Bricks.
2. **Fingerprinting**: Every Brick must have a unique hash based on its content and source path.
3. **Promotion Boundary**: Bricks remain in `SyncDatabase` until explicitly promoted to the Graph Layer.

### Cognition Boundaries
- **Synthesis Approval**: Relationships inferred by `RelationshipSynthesizer` are created with a `DRAFT` status unless auto-promotion is enabled for high-confidence scores (>0.9).
- **Context Assembly**: `assemble_topic` must prioritize `FROZEN` intents over `DRAFT` intents when resolving conflicts.

## 3. Governance & Security

### Auditability
- **Every** write operation (promotion, kill, supersede) MUST be logged via `GraphManager._log_audit_event`.
- **Actor Attribution**: Every state change must record the `actor` (agent_id or user_id) responsible for the action.

### Error Handling
- **Failed LLM Calls**: If the `LLMClient` fails during compilation, the run must be marked as `FAILED` in `SyncDatabase` to prevent partial/corrupt data ingestion.
- **Governance Violation**: Any prompt modification that bypasses `PromptManager` versioning is flagged as a `GovernanceViolation`.

## 4. Status Classification System
- ✅ **Confirmed**: Fully implemented, tested, and integrated.
- 🟡 **Partial**: Logic exists but is incomplete or lacks full integration.
- 🔴 **Missing**: Defined in architecture but not yet implemented.
- 🧪 **Mocked**: Simulation/placeholder logic in place for testing.
