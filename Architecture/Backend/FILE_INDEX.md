# File Index & Code Intelligence

## 1. Services Layer (`services/cortex`)

### `services/cortex/server.py`
**Entry Point**: Main Flask Application.
*   **Risk**: MED (External Surface)
*   **Classes**: None (Function-based Views)
*   **Key Functions**:
    *   `metrics_overview()`: READ-ONLY. Fetches DB stats.
    *   `jarvis_anchor()`: WRITE. Promotes/Rejects bricks (delegates to GraphManager).
    *   `cognition_assemble()`: WRITE. Enqueues async tasks.

### `services/cortex/worker.py`
**Core Infrastructure**: Postgres-backed Worker.
*   **Risk**: HIGH (Transactional Integrity)
*   **Class**: `PGWorker`
    *   `run_once()`: **Transactional**. Claims task -> Executes -> Marks Complete. **Idempotent**.
    *   `_cleanup_stalled_tasks()`: **Maintenance**. Resets stuck locks. **Safe**.

### `services/cortex/orchestration.py`
**Infrastructure**: Task Queue Interface.
*   **Risk**: MED (Queue Management)
*   **Class**: `TaskQueue`
    *   `enqueue(task_type, payload)`: **Write**. Inserts into `graph.l3_tasks`. **Safe**.

## 2. Graph Core (`src/nexus/graph`)

### `src/nexus/graph/manager.py`
**The Nervous System**: Unified Graph Manager.
*   **Risk**: **CRITICAL** (State Mutation)
*   **Class**: `GraphManager`
    *   `register_node(type, id, attrs)`: **Write**. Upserts node data. **Idempotent**.
    *   `register_edge(src, dst, type)`: **Write**. Creates relationship. **Idempotent**.
    *   `_check_for_cycle(start, end, type)`: **Read/Compute**. DFS for cycle detection. **Pure**.
    *   `promote_node_to_frozen(id)`: **Write**. State transition `FORMING` -> `FROZEN`. **Strict Invariants**.
    *   `supersede_node(old, new)`: **Write**. Links two nodes, updates lifecycle. **Strict Invariants**.
    *   `_log_audit_event(...)`: **Write**. Appends to `governance.audit_trace`. **Safe**.

## 3. Cognition Engine (`src/nexus/cognition`)

### `src/nexus/cognition/l3_sage.py`
**The Brain**: Strategic Auditor.
*   **Risk**: MED (LLM Calls, Cost)
*   **Class**: `L3Sage`
    *   `audit_topic_health(topic_id)`: **Complex**. Fetches metrics -> Prompts LLM -> Computes Confidence. **Read-Only (Side-effects: Logs)**.
    *   `_fetch_topic_metrics(topic_id)`: **Read**. Aggregates graph stats. **Pure**.

### `src/nexus/cognition/escalation_router.py` (Inferred)
**Routing Logic**: Model Selection.
*   **Risk**: LOW (Logic)
*   **Class**: `EscalationRouter`
    *   `route_l3(...)`: **Read/Compute**. Decides between Flash/Pro models.

### `src/nexus/cognition/confidence_engine.py` (Inferred)
**Trust Scoring**: Heuristics.
*   **Risk**: LOW (Math)
*   **Class**: `ConfidenceEngine`
    *   `compute_l3_confidence(...)`: **Pure**. Calculates score 0.0-1.0.

## 4. Ingestion (`src/nexus/sync`)

### `src/nexus/sync/runner.py`
**Ingestion Pipeline**: Deterministic Loader.
*   **Risk**: MED (Bulk Writes)
*   **Functions**:
    *   `run_sync(input_json)`: **Orchestrator**. Loads file -> Split -> Compile -> Persist. **Idempotent**.

### `src/nexus/sync/compiler.py` (Inferred)
**Transformation**: Text to Brick.
*   **Class**: `NexusCompiler`
    *   `compile_run(run_id)`: **Write**. Extracts bricks from source runs.

### `src/nexus/sync/db.py` (Inferred)
**Vault Storage**: Raw Ingestion DB.
*   **Class**: `SyncDatabase`
    *   `register_run_safe(...)`: **Write**. Stores raw conversation trees.
