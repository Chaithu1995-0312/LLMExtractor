# RULES_AND_INVARIANTS

## 1. Lifecycle Monotonicity
- **Invariant:** A node in the `FROZEN` state CANNOT transition back to `FORMING` or `LOOSE`.
- **Invariant:** A node in the `KILLED` state CANNOT transition to any other state.
- **Rule:** `FORMING` nodes are candidates for `FROZEN`. `LOOSE` nodes are candidates for `FORMING`.
- **Reasoning:** To preserve the stability of the knowledge graph, authoritative information (`FROZEN`) must be immutable.

## 2. Supersession Logic
- **Invariant:** A node cannot supersede itself.
- **Invariant:** A node can only be superseded by another `FROZEN` node.
- **Rule:** Supersession creates a directed edge `SUPERSEDED_BY`.
- **Reasoning:** Supersession is a historical record of "changing one's mind". Both the old and new truth must be preserved for auditability.

## 3. Graph Integrity
- **Invariant:** Every `Edge` must connect two existing `Nodes`.
- **Invariant:** All `Nodes` must have a unique `ID` (UUID or hash-based).
- **Rule:** `Topic` nodes are merged by slug to prevent fragmentation.
- **Rule:** `Artifact` nodes are content-addressable (SHA256) and immutable.

## 4. Conflict Resolution
- **Rule (Anchor Priority):** If a new incoming fact conflicts with an existing `FROZEN` intent (Similarity > 0.85), the `FROZEN` intent acts as an anchor and overrides the new fact.
- **Rule (Freshness Priority):** If a new incoming fact conflicts with an existing `FORMING` intent, the new fact supersedes the old `FORMING` intent (assuming latest data is better for forming ideas).

## 5. Persistence
- **Invariant:** All graph mutations must be persisted to SQLite immediately.
- **Invariant:** `Artifact` JSON payloads are stored on disk and never modified after creation.
