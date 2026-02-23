# Implementation Reality Map

## 1. Core Graph & Storage
| Component | Status | Notes |
| :--- | :---: | :--- |
| **Unified Node Storage** | ✅ | Implemented in `GraphManager`. JSONB payload `graph.nodes`. |
| **Edge Management** | ✅ | Implemented `graph.edges`. Supports typed edges & metadata. |
| **Invariants / Guardrails** | ✅ | Cycle detection (DFS), Lifecycle Monotonicity enforced in code. |
| **Audit Trace** | ✅ | `governance.audit_trace` table populated by `GraphManager`. |
| **Vector Index** | 🟡 | `nexus.vector` exists but integration with main graph queries is loose. |

## 2. Cognition Engine (The Brain)
| Component | Status | Notes |
| :--- | :---: | :--- |
| **L3 Sage** | ✅ | Full implementation: Strategic Audit, Hybrid Escalation. |
| **Escalation Router** | ✅ | Routes between Flash/Pro models based on difficulty/cost. |
| **Confidence Engine** | ✅ | Computes composite confidence scores (Model + Heuristics). |
| **Budget Controller** | ✅ | Tracks token usage and pressure. |
| **L2 Narrator** | 🟡 | Reference to `_emit_pulse`, but the consumption side (UI/Logs) is basic. |

## 3. Ingestion & Sync
| Component | Status | Notes |
| :--- | :---: | :--- |
| **Sync Pipeline** | ✅ | Deterministic ingestion from conversation logs (`src/nexus/sync`). |
| **Compiler** | ✅ | Compiles raw text into "Bricks". |
| **Vault (Sync DB)** | ✅ | Dedicated SQLite/PG abstraction for raw ingestion state. |
| **Tree Splitter** | ✅ | Breaks conversations into linear "Source Runs". |

## 4. Orchestration & Infrastructure
| Component | Status | Notes |
| :--- | :---: | :--- |
| **Task Queue** | ✅ | **Custom Postgres Queue** (`graph.l3_tasks`). |
| **Celery / Redis** | 🔴 | **Diverted**. Dependencies exist in `pyproject.toml` but unused in favor of PG Queue. |
| **Worker** | ✅ | `PGWorker` implements atomic claim/execute/complete transactions. |
| **API Server** | ✅ | Flask-based. Handles HTTP + SocketIO. |
| **Deployment** | 🧪 | Run scripts exist (`services/cortex/server.py`), but no Docker/K8s manifests visible in context. |

## 5. User Interface (Jarvis)
| Component | Status | Notes |
| :--- | :---: | :--- |
| **Graph Visualization** | 🟡 | Endpoints (`/jarvis/graph-index`) exist, but return raw JSON. |
| **Anchor/Promote** | ✅ | API endpoints implemented for graph manipulation. |
| **Ask / Preview** | ✅ | RAG preview endpoint implemented (`/jarvis/ask-preview`). |

## 6. Diverted / Scrap Code
*   **Legacy Sync**: Old sync scripts in `scripts/` might be obsolete compared to `src/nexus/sync`.
*   **Redis Dependencies**: `redis` package in `pyproject.toml` is effectively dead weight.
*   **Celery**: `celery` package in `pyproject.toml` is unused.
