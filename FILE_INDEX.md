# FILE INDEX

## 1. Directory Structure Overview
This index maps the physical file structure to logical architectural components, including risk profiles and key methods.

## 2. Source Code Inventory

### `src/nexus/sync/`
*   **`router.py`**
    *   `TopicRouter`
        *   `route_brick(brick_id)`: Assigns topic to brick. [Risk: MED]
*   **`sync_agent.py`** (Script)
    *   `SyncAgent`
        *   `run_sync_loop()`: Main ingestion loop. [Risk: MED]
*   **`db.py`**
    *   `PostgresConnection`
        *   `get_connection()`: Establishes DB link. [Risk: HIGH]

### `src/nexus/bricks/`
*   **`brick_store.py`**
    *   `BrickStore`
        *   `add_brick(content, metadata)`: Persists raw brick. [Risk: LOW]
        *   `get_brick(brick_id)`: Retrieves brick. [Risk: LOW]

### `src/nexus/graph/`
*   **`manager.py`**
    *   `GraphManager`
        *   `create_node(node_data)`: Creates conceptual node. [Risk: MED]
        *   `create_edge(source, target, type)`: Links nodes. [Risk: MED]

### `src/nexus/cognition/`
*   **`entity_resolver.py`**
    *   `EntityResolver`
        *   `resolve(node_a, node_b)`: Checks if nodes are same entity. [Risk: HIGH]
*   **`compiler.py`**
    *   `CognitiveCompiler`
        *   `compile_bricks(topic_id)`: Synthesizes bricks into nodes. [Risk: HIGH]
*   **`promotion_engine.py`**
    *   `PromotionEngine`
        *   `promote_node(node_id)`: Elevates node to higher abstraction. [Risk: MED]

### `services/cortex/`
*   **`api.py`**
    *   `FastAPI App`: Entry point for REST API.
        *   `GET /health`: System status. [Risk: LOW]
        *   `POST /query`: Semantic search endpoint. [Risk: MED]
*   **`worker.py`**
    *   `Celery/RabbitMQ Worker`: Async task processor.
        *   `process_task(task_payload)`: Executes background jobs. [Risk: MED]

## 3. Configuration & Scripts
*   **`scripts/`**
    *   `apply_cognition_schema.py`: Migrates DB schema for cognition. [Risk: HIGH]
    *   `test_drift_engine.py`: Validates concept drift logic. [Risk: LOW]
