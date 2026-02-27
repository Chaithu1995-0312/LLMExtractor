# CANONICAL OVERVIEW

## 1. Primary Purpose
Nexus is an AI-driven knowledge synthesis and cognitive architecture platform. It integrates unstructured data (e.g., chat logs, documents) into a unified knowledge graph and vector store, applying multi-layered cognition for routing, summarization, entity resolution, and conceptual evolution over time. It is built for autonomous agentic operations, enabling a machine-readable memory system that can process, compile, and evolve knowledge autonomously.

## 2. External Surface Map & Failure Modes

| Dependency | Purpose | Risk Profile | Failure Mode / Mitigation |
|------------|---------|--------------|---------------------------|
| PostgreSQL / pgvector | Graph persistence, relational state, vector store | HIGH | Connection loss, OOM, Vector index corruption / Managed via automated retries and `sync` invariants |
| LLM API (e.g., OpenAI / Ollama) | Text embeddings, Summarization, Narrative generation | HIGH | Rate limits, Context window overflow, Model deprecation / Managed via `budget_controller` and exponential backoff |
| RabbitMQ / PG Queue | Asynchronous task orchestration and L3 processing | MED | Queue backup, Poison pill messages / Managed via Dead Letter Queues (DLQ) and `escalation_router` |
| Redis (Optional/Caching) | Session state, Rate limiting, Fast ephemeral lookup | LOW | Cache eviction / Graceful degradation to DB lookup |

## 3. Data & State Modeling

### 3.1 Primary Data Schemas
*   **Brick:** The atomic unit of unstructured knowledge (e.g., a single message or paragraph).
*   **Node:** A conceptual entity derived from one or more Bricks.
*   **Edge:** The relationship between Nodes.
*   **Vector/Embedding:** High-dimensional representation of Bricks/Nodes for semantic search.
*   **Topic/Intent:** High-level categorization used for routing.

### 3.2 State Transition Logic
*   `Status: INGESTED` -> `Status: EMBEDDED` (via `sync_agent`)
*   `Status: EMBEDDED` -> `Status: COMPILING` (via `cognitive_compiler`)
*   `Status: COMPILING` -> `Status: RESOLVED` (via `entity_resolver`)
*   `Status: RESOLVED` -> `Status: PROMOTED` (via `promotion_engine`)

## 4. Entry Point Mapping

*   **CLI:** `src/nexus/cli/` (e.g., `scripts/sync_agent.py`, `scripts/apply_cognition_schema.py`) - For batch ingestion, schema migration, and manual triggers.
*   **API:** `services/cortex/api.py`, `services/cortex/server.py` - REST endpoints for UI (Jarvis) and external queries.
*   **Events:** `services/cortex/worker.py`, `services/cortex/tasks.py` - Background processors listening to PG Queues for async processing (L3 tasks, compaction).
