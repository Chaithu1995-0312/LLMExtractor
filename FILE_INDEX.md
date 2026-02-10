# FILE_INDEX

## 1. Core Logic (`src/nexus`)

### `src/nexus/sync/compiler.py`
**Class:** `NexusCompiler`
**Responsibility:** Compiles raw messages into structured Bricks.
| Method | Responsibility | Risk | Inputs | Output | Idempotency | State Impact |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `compile_run` | Orchestrates the compilation of a run. | MED | `run_id`, `topic_id` | `count` (int) | ✅ | Writes Bricks to DB. |
| `_reject_message` | Filters out low-value messages. | LOW | `msg` (dict) | `bool` | ✅ | None. |
| `_materialize_brick` | Converts a pointer into a persisted Brick. | MED | `run_data`, `pointer` | `Optional[Dict]` | ✅ | Saves Brick to DB. |

### `src/nexus/sync/db.py`
**Class:** `SyncDatabase`
**Responsibility:** Low-level SQLite wrapper for Ingestion data.
| Method | Responsibility | Risk | Inputs | Output | Idempotency | State Impact |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `create_topic` | Creates a new topic record. | MED | `topic_id`, `display_name` | None | ✅ | INSERT Topic. |
| `register_run` | Logs a new ingestion run. | MED | `run_id`, `content` | None | ✅ | INSERT Run. |
| `save_brick` | Persists a Brick. | MED | `brick` (dict) | None | ✅ | INSERT/UPDATE Brick. |

### `src/nexus/graph/manager.py`
**Class:** `GraphManager`
**Responsibility:** Manages the Knowledge Graph (Nodes, Edges).
| Method | Responsibility | Risk | Inputs | Output | Idempotency | State Impact |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `register_node` | Creates or updates a graph node. | MED | `type`, `id`, `attrs` | None | ✅ | UPSERT Node. |
| `register_edge` | Creates a directed edge. | MED | `src`, `dst`, `type` | None | ✅ | INSERT Edge. |
| `kill_node` | Marks a node as deprecated/killed. | HIGH | `node_id`, `reason` | None | ❌ | UPDATE Node Status. |
| `_check_for_cycle` | Detects cycles before edge creation. | LOW | `start`, `target` | `List[str]` | ✅ | None. |

### `src/nexus/graph/schema.py`
**Classes:** `Intent`, `Source`, `ScopeNode`, `Edge`
**Responsibility:** Data Transfer Objects and Enums.
- **Pure Data Classes:** No risk, purely structural definitions.

### `src/nexus/cognition/synthesizer.py`
**Module Level Functions**
**Responsibility:** High-level relationship extraction.
| Method | Responsibility | Risk | Inputs | Output | Idempotency | State Impact |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `run_relationship_synthesis` | Batch process topics to find edges. | HIGH | `topic_id` | None | ✅ | Creates Edges in Graph. |

## 2. Services (`services/cortex`)

### `services/cortex/api.py`
**Class:** `CortexAPI`
**Responsibility:** Business logic facade for the API.
| Method | Responsibility | Risk | Inputs | Output | Idempotency | State Impact |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `route` | Determines intent of user query. | LOW | `query` | `Dict` | ✅ | None. |
| `generate` | Generates a response using Agent/Bricks. | MED | `query`, `context` | `Dict` | ✅ | Audit Log Write. |
| `resolve_alert` | Resolves a governance alert. | HIGH | `alert_id`, `action` | `Dict` | ❌ | UPDATE Alert Status. |

### `services/cortex/gateway.py`
**Class:** `JarvisGateway`
**Responsibility:** Interface for external clients.
| Method | Responsibility | Risk | Inputs | Output | Idempotency | State Impact |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `pulse` | Sends a heartbeat/status update. | LOW | `event`, `context` | `str` | ✅ | None. |

## 3. UI (`ui/jarvis`)

### `ui/jarvis/src/store.ts`
**Hook:** `useNexusStore`
**Responsibility:** Client-side state management.
- **Actions:** `setMode`, `setSelectedBrickId`, `setSelectedNodeId`.
- **Risk:** LOW (Client-side memory only).
