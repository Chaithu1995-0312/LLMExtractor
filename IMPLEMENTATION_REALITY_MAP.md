# Implementation Reality Map

## 1. Core Graph Engine (`src/nexus/graph`)
| Component | Status | Implementation Details |
| :--- | :---: | :--- |
| **Storage Backend** | ✅ | SQLite (`graph.db`). Tables: `nodes`, `edges`. |
| **Schema Definition** | ✅ | Dataclasses + Enums (`schema.py`). Supports Intents, Scopes, Sources. |
| **Manager API** | ✅ | `GraphManager` handles CRUD, constraints, and transactions. |
| **Lifecycle Logic** | ✅ | State machine enforced in `promote_intent` (Monotonicity checks). |
| **Projections** | 🟡 | `projection.py` exists but integration with full pipeline is manual. |

## 2. Ingestion & Sync (`src/nexus/sync`, `src/nexus/bricks`)
| Component | Status | Implementation Details |
| :--- | :---: | :--- |
| **History Ingestion** | ✅ | `ingest_history.py` parses `conversations.json` efficiently. |
| **Brick Extraction** | ✅ | Splits messages by double newlines. Simple heuristic. |
| **Vector Embedding** | ✅ | `LocalVectorIndex` uses FAISS + `sentence-transformers`. |
| **Incremental Sync** | 🟡 | Logic exists but robustness on large updates is unverified. |

## 3. Cognition & Intelligence (`src/nexus/cognition`)
| Component | Status | Implementation Details |
| :--- | :---: | :--- |
| **DSPy Integration** | 🧪 | `dspy_modules.py` defines signatures for Facts/Diagrams. |
| **Topic Assembly** | 🟡 | `assembler.py` orchestrates extraction but lacks complex reasoning loops. |
| **Reranking** | 🟡 | `cross_encoder.py` exists; integration in recall pipeline is partial. |

## 4. Service Layer (`services/cortex`)
| Component | Status | Implementation Details |
| :--- | :---: | :--- |
| **REST API** | ✅ | Flask server exposing Graph, Anchor, and Assembly endpoints. |
| **MCP Server** | 🧪 | `nexus_server.py` implements Model Context Protocol (experimental). |
| **Orchestration** | 🟡 | Basic task running; no full job queue system. |

## 5. User Interface (`ui/jarvis`)
| Component | Status | Implementation Details |
| :--- | :---: | :--- |
| **Visualization** | 🟡 | React + generic node rendering. |
| **Interaction** | 🟡 | Basic "Promote/Reject" actions wired to API. |
| **State Management** | 🟡 | Simple local store; no robust real-time sync. |

## 6. Infrastructure & Testing
| Component | Status | Implementation Details |
| :--- | :---: | :--- |
| **Unit Tests** | ✅ | `tests/unit` covers core logic. |
| **Invariant Tests** | ✅ | `tests/invariants` covers lifecycle and graph integrity. |
| **CI/CD** | 🔴 | No visible GitHub Actions or CI configuration. |
