import os

docs = {
    "Architecture/Backend/CANONICAL_OVERVIEW.md": """# Canonical Overview

## System Purpose
Nexus is an intelligent event-driven processing pipeline and cognitive architecture.

## Status Classification
- ✅ Implemented
- 🟡 Partial
- 🔴 Missing
- 🧪 Mocked

## Architecture Layers
1. **Ingestion Layer**
2. **Graph Layer**
3. **Cognition Layer**
4. **Service Layer**
""",
    "Architecture/Backend/IMPLEMENTATION_REALITY_MAP.md": """# Implementation Reality Map

## Component Status

### Graph Layer
- `NexusGraphManager` ✅ Implemented
- `SchemaEvolution` 🟡 Partial

### Cognition Layer
- `L3Sage` 🧪 Mocked
- `ConfidenceEngine` 🔴 Missing

## Class -> Method Map (Reality)

### NexusGraphManager
- `execute_query` ✅
- `build_projection` 🟡

""",
    "Architecture/Backend/FILE_INDEX.md": """# File Index

## `src/nexus/graph/manager.py`
Classes:
- `NexusGraphManager`
  - `execute_query`: Executes Cypher queries against the graph DB.
  - `build_projection`: Creates a specialized sub-graph projection.

## `src/nexus/cognition/l3_sage.py`
Classes:
- `L3Sage`
  - `synthesize`: IMPLIED - Synthesizes context into a coherent response.
""",
    "Architecture/Backend/MODULE_DEEP_DIVES.md": """# Module Deep Dives

## Graph Module
### `NexusGraphManager`
#### Method Intelligence
| Method | Responsibility | Inputs | Outputs/Side Effects | Invariants | Failure Modes |
|--------|----------------|--------|----------------------|------------|---------------|
| `execute_query` | Query execution | `query`, `params` | DB state mutation / results | Valid connection | Timeout, Syntax Error |

**Usage Graph**: Called by `Service Layer`, `Cognition Layer`. Stateful, Write-authoritative.
""",
    "Architecture/Backend/RULES_AND_INVARIANTS.md": """# Rules and Invariants

## Core Invariants
1. **Graph Integrity**: Nodes must have a `uuid`.
2. **Cognition Lifecycle**: Confidence scores must be >= 0 and <= 1.

## Method Invariants
- `execute_query`: Must run within an active transaction.
""",
    "Architecture/Backend/GAPS_AND_TODOS.md": """# Gaps and Todos

## Critical Gaps
1. 🔴 `ConfidenceEngine` is missing.
2. 🟡 Sub-graph projection is incomplete.

## Missing Methods
- `L3Sage.synthesize` (🧪)
""",
    "Architecture/Backend/INFERRED_ENHANCEMENTS.md": """# Inferred Enhancements

## Optimizations
- Caching layer for `execute_query`.
- Asynchronous query execution.
""",
    "Architecture/Backend/APPENDIX.md": """# Appendix

## Consolidated Class -> Method -> Responsibility -> Used By

| Class | Method | Responsibility | Used By |
|-------|--------|----------------|---------|
| `NexusGraphManager` | `execute_query` | Query execution | `CortexWorker` |
| `L3Sage` | `synthesize` (IMPLIED) | Context synthesis | `Orchestrator` |

"""
}

for path, content in docs.items():
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

print("Documents generated successfully.")