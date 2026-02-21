# CANONICAL_OVERVIEW.md
> System: **Nexus Cognitive Knowledge Engine**
> Version: 0.1.0 | Last Inspected: 2026-02-18
> Status Legend: ✅ Implemented | 🟡 Partial | 🔴 Missing | 🧪 Mocked/Stub

---

## 1. System Identity

**Nexus** is an agentic, self-organizing knowledge extraction and retrieval system. It ingests raw conversation histories (exported ChatGPT JSON), compiles them into atomic knowledge units ("bricks"), organizes bricks into a typed knowledge graph (intents, scopes, edges), and exposes a multi-tier LLM query/synthesis interface to a browser-based operational dashboard (Jarvis UI).

The system operates across four architectural planes:

| Plane | Name | Responsibility |
|---|---|---|
| 1 | **Ingestion / Sync** | Parse source JSON → extract bricks → commit to vault |
| 2 | **Graph / Governance** | Store bricks as graph nodes; enforce lifecycle FSM; track audit trail |
| 3 | **Cognition** | Recall → rerank → assemble → synthesize knowledge artifacts |
| 4 | **UI / Realtime** | React dashboard (Jarvis) consuming REST + WebSocket events from Cortex |

---

## 2. High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         JARVIS UI (React/Vite)              │
│  Zustand stores: graph-store / system-store / stream-store  │
│  FSM: GlobalSystemFSM / CognitiveEngineFSM / StreamFSM      │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP REST + WebSocket (SocketIO)
┌──────────────────────▼──────────────────────────────────────┐
│                    CORTEX SERVER (Flask + SocketIO :5001)   │
│  CortexAPI · JarvisGateway · Celery Tasks                   │
└───┬──────────────┬──────────────┬──────────────┬────────────┘
    │              │              │              │
    ▼              ▼              ▼              ▼
GraphManager  SyncDatabase  Cognition     JarvisGateway
(graph layer) (sync layer)  (assembler/   (LLM router)
                             sentinel)
    │              │              │
    └──────────────┴──────────────┘
                   │
         ┌─────────▼──────────┐
         │  PostgreSQL DB     │
         │  schema: sync /    │
         │  graph /           │
         │  governance        │
         └────────────────────┘
                   │
         ┌─────────▼──────────┐
         │  FAISS Local Index │
         │  (384-dim vectors) │
         └────────────────────┘
                   │
         ┌─────────▼──────────┐
         │  Ollama (local LLM)│
         │  http://3.109...   │
         └────────────────────┘
```

---

## 3. Module Inventory

| Module | Path | Status | Purpose |
|---|---|---|---|
| Config | `src/nexus/config.py` | ✅ | Path constants, environment variable bindings |
| DB Adapter | `src/nexus/db/adapter.py` | ✅ | Abstract DB interface |
| DB Postgres | `src/nexus/db/postgres.py` | ✅ | psycopg2 connection pool implementation |
| DB Init | `src/nexus/db/init_db.py` | ✅ | Schema bootstrap from SQL file |
| Graph Schema | `src/nexus/graph/schema.py` | ✅ | Dataclasses + Enums (Intent, Edge, Lifecycle, etc.) |
| Graph Manager | `src/nexus/graph/manager.py` | 🟡 | Node/edge CRUD, lifecycle transitions, audit — has SQLite residue |
| Graph Prompt Manager | `src/nexus/graph/prompt_manager.py` | ✅ | Prompt versioning + governance audit |
| Graph Projection | `src/nexus/graph/projection.py` | ✅ | Intent → WallCell classifier |
| Graph Validation | `src/nexus/graph/validation.py` | ✅ | Invariant validators (cycles, orphans, scope) |
| Sync Runner | `src/nexus/sync/runner.py` | ✅ | CLI entry point for ingestion pipeline |
| Sync Compiler | `src/nexus/sync/compiler.py` | ✅ | Core LLM-powered extraction pipeline |
| Sync LLM | `src/nexus/sync/llm.py` | 🟡 | LLM router + Ollama client (OpenAI/Claude stubs only) |
| Sync DB | `src/nexus/sync/db.py` | ✅ | Postgres-native CRUD for topics, runs, bricks |
| Bricks Extractor | `src/nexus/bricks/extractor.py` | ✅ | Block-aware brick extraction from tree files |
| Bricks Resolver | `src/nexus/bricks/resolver.py` | ✅ | User-triggered LOOSE→FORMING resolver |
| Bricks Store | `src/nexus/bricks/brick_store.py` | 🔴 | Uses SQLite-only `_get_conn()` — broken on Postgres |
| Ask Recall | `src/nexus/ask/recall.py` | ✅ | FAISS + ACL + rerank pipeline |
| Vector Index | `src/nexus/vector/local_index.py` | ✅ | FAISS IndexFlatL2, 384-dim |
| Embedder | `src/nexus/vector/embedder.py` | ✅ | SentenceTransformer `all-MiniLM-L6-v2`, optional GPT rewrite |
| Rerank Orchestrator | `src/nexus/rerank/orchestrator.py` | ✅ | 3-stage fallback: LLM → CrossEncoder → Heuristic |
| Rerank LLM | `src/nexus/rerank/llm_reranker.py` | 🟡 | llama-cpp-python, requires `.gguf` model file |
| Cognition Assembler | `src/nexus/cognition/assembler.py` | ✅ | Full artifact assembly with graph topology awareness |
| Cognition DSPy | `src/nexus/cognition/dspy_modules.py` | ✅ | DSPy signatures + modules for extraction/synthesis |
| Cognition Synthesizer | `src/nexus/cognition/synthesizer.py` | ✅ | Relationship discovery via DSPy batch processing |
| Coverage Sentinel | `src/nexus/cognition/coverage_sentinel.py` | ✅ | LLM-based structural gap detection |
| Coverage Scorer | `src/nexus/cognition/coverage_scorer.py` | ✅ | Numeric score formula using alert counts + stability |
| Prompt Generator | `src/nexus/cognition/prompt_generator.py` | 🟡 | Alert→prompt generation; known schema bug |
| Governance Alert Manager | `src/nexus/governance/alert_manager.py` | 🔴 | Uses SQLite directly — not Postgres-compatible |
| Cortex Server | `services/cortex/server.py` | 🟡 | Flask+SocketIO API; SQLite used for metrics |
| Cortex API | `services/cortex/api.py` | ✅ | Business logic facade over all backend components |
| Cortex Gateway | `services/cortex/gateway.py` | 🟡 | L1/L2/L3 LLM router; L2/L3 real calls not wired |
| Cortex Orchestration | `services/cortex/orchestration.py` | 🧪 | LangGraph self-correction workflow (simulated) |
| Cortex Tasks | `services/cortex/tasks.py` | ✅ | Celery task wrappers |
| Jarvis UI | `ui/jarvis/src/` | ✅ | React/Vite/Zustand/Tailwind dashboard |

---

## 4. Data Flow (Primary Ingestion Path)

```
[Raw ChatGPT Export JSON]
        │
        ▼
run_sync() [sync/runner.py]
        │
        ├─► load_conversations() → process_conversation() → tree files on disk
        │
        ├─► SyncDatabase.register_run(run_id, tree_content)
        │
        └─► NexusCompiler.compile_run(run_id, topic_id)
                │
                ├─► _pre_filter_nodes()    [Signal gate + role gate]
                ├─► _build_batches()       [Bounded batching]
                ├─► _llm_extract_pointers() [StructuredIngestLLM → Ollama]
                ├─► _materialize_brick()   [Zero-trust verbatim gate]
                ├─► SyncDatabase.save_brick() [Dual write: sync.bricks + graph.nodes]
                └─► CoverageSentinel.analyze_topic() [Optional post-pass]
```

---

## 5. Data Flow (Query / Recall Path)

```
[User Query]
        │
        ▼
recall_bricks_readonly() [ask/recall.py]
        │
        ├─► VectorEmbedder.embed_query()
        ├─► LocalVectorIndex.search()     [FAISS k-NN]
        ├─► BrickStore.get_brick_metadata() [scope ACL filter]
        └─► RerankOrchestrator.rerank()   [LLM → CrossEncoder → Heuristic]
                │
                ▼
         [Ranked brick list + confidence scores]
                │
                ▼
        assemble_topic() [cognition/assembler.py]
                │
                ├─► CognitiveExtractor.forward() [DSPy]
                ├─► GraphManager (topology-aware conflict resolution)
                └─► Artifact JSON persisted to disk
```

---

## 6. Primary Data Schemas

### 6.1 Intent (graph node)
```
{
  "id": "uuid",
  "type": "intent",
  "data": {
    "statement": "string",
    "lifecycle": "loose | forming | frozen | superseded | killed",
    "intent_type": "rule | fact | formula | structure | question | goal | unknown",
    "metadata": {}
  },
  "created_at": "timestamptz"
}
```

### 6.2 Brick (sync + graph node)
```
{
  "id": "sha256[:32]",
  "topic_id": "string",
  "content": "string (verbatim quote)",
  "fingerprint": "sha256 of normalized content",
  "state": "IMPROVISE | FORMING | FINAL | SUPERSEDED",
  "run_id": "string",
  "json_path": "$.messages[N].content",
  "start_index": int,
  "end_index": int,
  "source_checksum": "sha256"
}
```

### 6.3 Coverage Alert
```
{
  "alert_id": "uuid",
  "fingerprint": "sha256",
  "topic_id": "string",
  "type": "FLOW_REDUNDANCY | COVERAGE_GAP | ORPHAN_BRICKS | CONTRADICTION | LOW_SIGNAL_TOPIC | ANALYSIS_WITHOUT_DECLARATION",
  "severity": "info | warning | critical",
  "signal_score": float,
  "state": "NEW | ACKNOWLEDGED | RESOLVED | DISMISSED | ARCHIVED",
  "summary": "string"
}
```

### 6.4 State Transitions

**Brick/Intent Lifecycle (monotonic)**
```
LOOSE (IMPROVISE) → FORMING → FROZEN (FINAL) → SUPERSEDED → KILLED
LOOSE → KILLED (direct rejection)
FORMING → KILLED (direct rejection)
```

**Coverage Alert Lifecycle**
```
NEW → ACKNOWLEDGED → RESOLVED → ARCHIVED
NEW → ACKNOWLEDGED → DISMISSED → ARCHIVED
NEW → DISMISSED (direct)
```

**UI Global System FSM**
```
BOOTING → READY → DEGRADED → CRITICAL → RECOVERING → READY
READY → CRITICAL (DB_FAILURE)
DEGRADED → READY (HEALTH_RESTORED)
```

---

## 7. Entry Points

| Entry Point | Type | Location | Trigger |
|---|---|---|---|
| `nexus sync` | CLI | `src/nexus/cli/main.py` | Manual / Cron |
| `run_sync()` | Function | `src/nexus/sync/runner.py` | CLI dispatch |
| `cortex/server.py __main__` | Process | `services/cortex/server.py` | `python server.py` |
| `POST /cognition/assemble` | HTTP | `services/cortex/server.py` | UI / API client |
| `POST /cognition/synthesize` | HTTP | `services/cortex/server.py` | UI / API client |
| `POST /tasks/sync` | HTTP | `services/cortex/server.py` | UI / API client |
| `GET /jarvis/graph-index` | HTTP | `services/cortex/server.py` | Jarvis UI on boot |
| `GET /jarvis/ask-preview` | HTTP | `services/cortex/server.py` | Jarvis UI query |
| `SocketIO connect` | WebSocket | `services/cortex/server.py` | Jarvis UI on boot |
| `sync_bricks_task` | Celery | `services/cortex/tasks.py` | Celery worker |
| `assemble_topic_task` | Celery | `services/cortex/tasks.py` | Celery worker |
| `python db/init_db.py` | Script | `src/nexus/db/init_db.py` | One-time setup |

---

## 8. External Surface Map (3rd Party Dependencies + Failure Modes)

| Dependency | Role | Location | Failure Mode |
|---|---|---|---|
| **PostgreSQL 16** | Primary database (sync, graph, governance schemas) | Docker `nexus-postgres:5432` | All write/read ops fail. `DatabaseURL` env required. Pool init throws `RuntimeError`. |
| **Ollama** (remote) | L1 local LLM inference | `http://127.0.0.1:11434` | `CONNECTION_FAILED` JSON returned. `LLM_STRICT_MODE=true` re-raises. Timeout configurable via `LLM_TIMEOUT` (default 600s). |
| **FAISS (faiss-cpu)** | Vector similarity search | In-process via LocalVectorIndex | If `.faiss` file absent: index starts empty, all searches return `[]`. Non-fatal. |
| **SentenceTransformers** (`all-MiniLM-L6-v2`) | Text embedding (384-dim) | In-process via VectorEmbedder | ImportError if not installed. Model download on first call. Single shared model instance. |
| **DSPy** | Structured LLM inference for cognition | In-process via dspy_modules | Depends on configured LLM backend; if Ollama offline, extraction returns empty. |
| **LiteLLM Proxy** | L2/L3 budget-gated cloud LLM | `http://0.0.0.0:4000` | HTTP 429 → `DAILY_BUDGET_EXCEEDED`. HTTP other → error dict. Connection failure returns `CONNECTION_FAILED`. |
| **OpenAI API** (GPT-4o / gpt-4o-mini) | L2/L3 LLM inference | Via `OPENAI_API_KEY` env var | Stubs in `LLMClient._call_openai()` return `STUB_OPENAI`. Not production-ready. |
| **Anthropic Claude** | L2/L3 LLM inference | Via LiteLLM proxy | Stubs in `LLMClient._call_claude()` return `STUB_CLAUDE`. Not production-ready. |
| **Celery + Redis** | Async task queue | `redis://localhost:6379` | Task dispatch fails silently; `HAS_CELERY=False` triggers synchronous fallback. |
| **llama-cpp-python** | L1 reranker (local GGUF model) | In-process via LlmReranker | `FileNotFoundError` if GGUF file absent — orchestrator falls through to CrossEncoder. |
| **Flask-SocketIO** | WebSocket transport for UI realtime | In-process | If socketio unavailable, `_log_audit_event` silently suppresses broadcast. |
| **LangGraph** | Agentic self-correction workflow | `services/cortex/orchestration.py` | Used in `cleanup_crew_workflow`; simulated nodes only — not wired to live LLM. |
| **jsonpath-ng** | JSON path resolution in compiler | `sync/compiler.py` | `ImportError` caught — falls back to manual path parsing. |
| **psycopg2-binary** | PostgreSQL driver | `db/postgres.py` | `RuntimeError` if `DATABASE_URL` not set. Connection pool: `minconn=1, maxconn=10`. |

---

## 9. Environment Variables

| Variable | Default | Required | Purpose |
|---|---|---|---|
| `DATABASE_URL` | None | ✅ | Postgres connection string |
| `LOCAL_LLM_ENABLED` | `true` | No | Enable/disable local Ollama |
| `LOCAL_LLM_PROVIDER` | `ollama` | No | LLM provider for L1 |
| `LOCAL_LLM_MODEL` | `phi3:latest` | No | Default Ollama model |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | No | Remote Ollama endpoint |
| `OPENAI_API_KEY` | None | No | Enables L2/L3 + query rewrite |
| `LLM_TIMEOUT` | `600` | No | Ollama HTTP timeout (seconds) |
| `LLM_STRICT_MODE` | `false` | No | Re-raise LLM errors instead of returning JSON error |
| `LLM_MOCK_INGEST` | `false` | No | Use mock responses in StructuredIngestLLM |
| `COGNITIVE_SHARD_LIMIT` | `10` | No | Max cognitive shards |

---

## 10. Infrastructure

| Component | Technology | Config |
|---|---|---|
| Backend Server | Flask 2.x + Flask-SocketIO | Port 5001 |
| Task Queue | Celery | Redis broker |
| Database | PostgreSQL 16 | Docker Compose |
| Vector Index | FAISS flat L2 | File-backed (`.faiss` + `.json`) |
| Frontend | React 18 + Vite + Tailwind | Port 5173 (dev) |
| Package Manager | pip / setuptools | `pyproject.toml` |
| Container | Docker Compose | `docker-compose.yml` |
