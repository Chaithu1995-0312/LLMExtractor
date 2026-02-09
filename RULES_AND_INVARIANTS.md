# Nexus: Rules and Invariants

## Agent Safety Rails
These are mandatory constraints that MUST be verified before any write operation to the Graph or Prompt database.

| Zone | Constraint | Verification Hook |
|------|------------|-------------------|
| **Graph Mutations** | No circular dependencies allowed for `DEPENDS_ON` edges. | `GraphManager._check_for_cycle` |
| **Lifecycle** | `FROZEN` nodes cannot be deleted; they must be `SUPERSEDED` or `KILLED`. | `GraphManager.delete_node` check |
| **Prompts** | System prompts must pass a "Safety Score" threshold (>0.7) before production use. | `PromptManager.save_prompt` / `GovernanceViolation` |
| **Bricks** | Duplicate bricks (by content hash) are rejected during materialization. | `NexusCompiler._materialize_brick` unique index |

## Mandatory Verification Hooks
- **Post-Sync Audit**: After `run_sync`, `validation.run_full_validation` must be executed to ensure graph integrity.
- **Write-Authoritative Boundary**: Only the `GraphManager` is permitted to execute `INSERT` or `UPDATE` statements on the graph schema. Direct SQL is prohibited for autonomous agents.
- **Lifecycle Gatekeeper**: The transition to `FROZEN` requires a successful execution of the `CoverageScorer` to ensure the topic is sufficiently documented.

## "Do Not Touch" Zones
1. **`src/nexus/graph/schema.py`**: The core data structures are immutable for automation. Any schema change requires a human architectural audit.
2. **`src/nexus/sync/db.py`**: Raw brick storage schema is locked to maintain historical provenance.
3. **Audit Trails**: The `graph_audit_log` table is append-only. Agents are strictly forbidden from modifying or deleting audit records.

## Structural Invariants
- **Orphan Prevention**: Every `Intent` node must have at least one edge of type `DERIVED_FROM` (to a Source/Brick) or `MEMBER_OF` (to a Scope).
- **Unique Identification**: Brick IDs are deterministic based on source file, content hash, and sequence index.
- **Atomic Transactions**: All multi-node graph updates MUST use the `GraphTransaction` context manager to ensure all-or-nothing persistence.
