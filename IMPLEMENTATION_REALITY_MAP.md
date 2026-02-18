# Implementation Reality Map

## 1. Module Status Overview

| Module | Path | Status | Notes |
| :--- | :--- | :--- | :--- |
| **Ingestion** | `src/nexus/sync` | ✅ | Full pipeline from JSON to DB implemented. |
| **Extraction** | `src/nexus/extract` | ✅ | `TreeSplitter` handles rich ingest and stable path hashing. |
| **Cognition** | `src/nexus/cognition` | ✅ | DSPy modules and Synthesizer active. |
| **Graph** | `src/nexus/graph` | ✅ | GraphDB, Schema, and Manager functional. |
| **API** | `services/cortex` | ✅ | Flask Server + Socket.IO + Celery Tasks. |
| **UI** | `ui/jarvis` | ✅ | React frontend with visualization components. |
| **Vector** | `src/nexus/vector` | ✅ | FAISS integration via `local_index.py`. |
| **Governance** | `src/nexus/governance` | 🟡 | `AlertManager` exists but runs partially detached from main sync. |
| **Reranking** | `src/nexus/rerank` | 🟡 | `LlmReranker` implemented with `llama-cpp` but optional. |
| **Testing** | `tests/` | 🟡 | Integration tests exist, unit coverage unclear. |

## 2. Class & Method Reality Check

### `src/nexus/sync/runner.py`
| Class/Method | Status | Intelligence |
| :--- | :--- | :--- |
| `run_sync` | ✅ | **Risk**: HIGH (DB Write). Orchestrates the entire ingestion. |
| `NexusCompiler` | ✅ | **Risk**: MED. Calls LLM, parses results. |
| `SyncDatabase` | ✅ | **Risk**: HIGH. Direct SQL/KV store access. |

### `src/nexus/extract/tree_splitter.py`
| Class/Method | Status | Intelligence |
| :--- | :--- | :--- |
| `process_conversation` | ✅ | **Risk**: MED. File IO. Converts JSON tree to linear paths. |
| `extract_message` | ✅ | **Risk**: LOW. Pure logic. Handles rich content parsing. |

### `src/nexus/graph/prompt_manager.py`
| Class/Method | Status | Intelligence |
| :--- | :--- | :--- |
| `get_prompt` | ✅ | **Risk**: MED. Enforces governance. Raises `GovernanceViolation`. |
| `save_prompt` | ✅ | **Risk**: HIGH. Writes to Governance DB. |

### `src/nexus/rerank/llm_reranker.py`
| Class/Method | Status | Intelligence |
| :--- | :--- | :--- |
| `rank` | ✅ | **Risk**: MED. Calls local LLM. Has latency fallback. |

## 3. Scrap / Diverted / Legacy Code

| Component | File | Status | Analysis |
| :--- | :--- | :--- | :--- |
| **BrickStore Legacy** | `src/nexus/bricks/brick_store.py` | 🔴 | `_load_all_bricks_metadata` is deprecated. Class wraps `SyncDatabase` redundantly. |
| **Walls Builder** | `src/nexus/walls/builder.py` | 🟡 | Seemingly standalone CLI tool for token-aware text dumping. Not integrated into `runner.py`. |
| **Legacy Indexing** | `src/nexus/index/conversation_index.py` | 🟡 | Separate JSON index. Potentially redundant with `SyncDatabase`. |

## 4. Missing or Implied Capabilities

| Feature | Implied Location | Status | Analysis |
| :--- | :--- | :--- | :--- |
| **Incremental Sync** | `runner.py` | 🟡 | Logic exists for `rebuild_index` but true incremental diffing is partial. |
| **Deep Conflict Resolution** | `synthesizer.py` | 🔴 | `RelationshipSynthesizer` finds conflicts, but resolution logic is thin. |
| **User Auth** | `services/cortex` | 🧪 | No real auth found; assumes local/trusted environment. |
| **Multi-Tenant Sharding** | `src/nexus/config.py` | 🔴 | Config points to single `graph.db`. |
