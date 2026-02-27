# IMPLEMENTATION REALITY MAP

## 1. System Components Status

| Component / Feature | Status | Notes |
|---------------------|--------|-------|
| PostgreSQL Database | ✅ | Core schema deployed |
| pgvector Extension | ✅ | Integrated for embedding storage |
| Ingestion Pipeline (`sync_agent`) | ✅ | Handles raw parsing |
| Brick Storage (`brick_store.py`) | ✅ | Core atomic storage |
| Topic Router (`router.py`) | 🟡 | Basic rules in place, LLM routing needs optimization |
| Graph Manager (`manager.py`) | ✅ | Node/Edge persistence functional |
| Cognitive Compiler | 🟡 | Early implementation, edge cases remaining |
| Entity Resolver (`entity_resolver.py`) | 🧪 | Mocked behavior, lacks robust LLM disambiguation |
| Promotion Engine (`promotion_engine.py`) | 🟡 | Implemented, requires tuning |
| L3 Sage (`l3_sage.py`) | 🔴 | Architecture defined, missing code |
| Cortex API (`api.py`) | ✅ | Serving UI |
| RabbitMQ Integration | 🔴 | Described in architecture, using PG queues currently |

## 2. Core Flows Verification

### Ingestion to Vector Store
**Status: ✅ Fully Implemented**
Data successfully flows from raw source -> Brick -> Embedding -> DB.

### Document Compilation (Cognition)
**Status: 🟡 Partial**
Compiles structured summaries, but recursive multi-document synthesis relies on strict thresholds that fail on heterogeneous data.

### Graph Evolution (Drift/Promotion)
**Status: 🧪 Experimental**
Mechanisms exist to detect drift, but confidence scoring is heavily mocked and not safely mutating the graph in production without manual review.

## 3. Class Method Map: Implementation Reality

### `src/nexus/sync/router.py` -> `TopicRouter`
*   **Method:** `route_brick(brick_id: str) -> TopicID`
*   **Responsibility:** Assign topic to incoming brick.
*   **Status:** 🟡 Needs better LLM prompt context.
*   **Risk Profile:** MED
*   **Inputs/Outputs:** `brick_id` -> `TopicID`
*   **Idempotency:** ✅ Yes
*   **State Impact:** Updates `brick.topic_id`
*   **Validation/Invariants:** Topic must exist in enum/schema.

### `src/nexus/cognition/entity_resolver.py` -> `EntityResolver`
*   **Method:** `resolve(node_a: Node, node_b: Node) -> bool`
*   **Responsibility:** Determine if two conceptual nodes represent the same real-world entity.
*   **Status:** 🧪 Mocked (returns True based on string matching).
*   **Risk Profile:** HIGH
*   **Inputs/Outputs:** `Node`, `Node` -> `boolean`
*   **Idempotency:** ✅ Yes
*   **State Impact:** None (Purely comparative, caller merges).
*   **Validation/Invariants:** Nodes must be of same type.

### `src/nexus/cognition/l3_sage.py` -> `L3Sage`
*   **Method:** `orchestrate_deep_thought(topic: str) -> Strategy`
*   **Responsibility:** Launch multi-step agentic deep dive.
*   **Status:** 🔴 MISSING_FROM_CONTEXT
*   **Risk Profile:** HIGH
*   **Inputs/Outputs:** `topic` -> `Strategy`
*   **Idempotency:** ❌ No
*   **State Impact:** Spawns async DB tasks, consumes LLM budget.
*   **Validation/Invariants:** Budget must be > 0.