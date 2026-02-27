# APPENDIX: Class & Method Reference

## 1. Core Logic Map

| Class | Method | Responsibility | Risk | Used By |
|-------|--------|----------------|------|---------|
| `TopicRouter` | `route_brick` | Assigns topic label | MED | `SyncAgent` |
| `BrickStore` | `add_brick` | Saves atomic content | LOW | `SyncAgent` |
| `CognitiveCompiler` | `compile_bricks` | Synthesizes nodes | HIGH | `SyncAgent`, `Worker` |
| `EntityResolver` | `resolve` | Merges duplicates | HIGH | `GraphManager`, `Worker` |
| `GraphManager` | `create_node` | DB write for nodes | MED | `Compiler`, `Resolver` |
| `GraphManager` | `create_edge` | DB write for edges | MED | `Compiler` |
| `PromotionEngine` | `promote_node` | Evolves node level | MED | `Worker` |
| `L3Sage` | `orchestrate` | Deep reasoning (Future) | HIGH | `API` |
| `PostgresConnection`| `get_connection`| DB Access | HIGH | *All* |

## 2. Terminology Glossary
*   **Brick:** Atomic unit of data (e.g., chat message).
*   **Node:** Synthesized concept derived from Bricks.
*   **Edge:** Relationship between Nodes.
*   **Topic:** High-level categorization domain.
*   **Cognition Level:**
    *   L1: Ingestion & Routing (Fast).
    *   L2: Compilation & Synthesis (Slow).
    *   L3: Deep Reasoning & Planning (Agentic).
