# Rules and Invariants

## Intent Lifecycle State Machine
The lifecycle of an Intent is strictly monotonic. Transitions generally move towards higher stability or finality.

- **Monotonicity**: An Intent cannot regress to a less stable state (e.g., `FROZEN` $\rightarrow$ `LOOSE` is illegal).
- **Valid Transitions**:
    - `LOOSE` $\rightarrow$ `FORMING` | `KILLED`
    - `FORMING` $\rightarrow$ `FROZEN` | `KILLED`
    - `FROZEN` $\rightarrow$ `SUPERSEDED` | `KILLED`
    - `SUPERSEDED` $\rightarrow$ `KILLED`
    - `KILLED` $\rightarrow$ $\emptyset$ (Terminal State)

## Graph Integrity Constraints

### 1. Scope Binding
**Invariant**: Any Intent entering the `FROZEN` state MUST have at least one outgoing `APPLIES_TO` edge pointing to a valid `ScopeNode`.
- *Enforcement*: Checked in `GraphManager.promote_intent` before state update commit.
- *Reasoning*: Canonical knowledge must be contextualized. Universal truths are rare; scoped truths are useful.

### 2. Override Stability
**Invariant**: An `OVERRIDES` edge can only be created if the source Intent is already `FROZEN`.
- *Enforcement*: Checked in `GraphManager.add_typed_edge`.
- *Reasoning*: You cannot override existing knowledge with a draft (LOOSE/FORMING). Only established facts can override other facts.

### 3. Single Override Principle
**Invariant**: A target Intent can be the destination of at most one `OVERRIDES` edge.
- *Enforcement*: Checked in `GraphManager.add_typed_edge`.
- *Reasoning*: prevents conflict chains. If multiple Intents override the same target, the conflict must be resolved into a single superior Intent first.

## Ingestion & Data Rules

### 1. Brick Atomicity
**Rule**: A Brick represents the smallest unit of coherent thought.
- *Definition*: Text blocks separated by double newlines (`\n\n`) in the source message.
- *Implication*: Context is preserved via metadata linkage to the original message, not within the Brick content itself.

### 2. Idempotency
**Rule**: All Graph and Vector operations must be idempotent.
- *Implementation*:
    - `GraphManager.register_node`: Updates if exists, inserts if new.
    - `GraphManager.register_edge`: Checks existence before insertion.
    - `LocalVectorIndex`: Stores processed Brick IDs to prevent duplicate embedding.

## API Contracts

### 1. Read-Write Separation
- **GET** requests (e.g., `graph-index`) MUST NOT modify the graph state.
- **POST** requests (e.g., `anchor`) MUST be transactional.

### 2. Error Propagation
- Service layer exceptions (e.g., `ValueError` from `GraphManager`) MUST be caught and mapped to appropriate HTTP 4xx status codes (e.g., 400 Bad Request for invariant violations).
