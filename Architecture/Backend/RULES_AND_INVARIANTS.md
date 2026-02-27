# Rules and Invariants

## Core Invariants
1. **Graph Integrity**: Nodes must have a `uuid`.
2. **Cognition Lifecycle**: Confidence scores must be >= 0 and <= 1.

## Method Invariants
- `execute_query`: Must run within an active transaction.
