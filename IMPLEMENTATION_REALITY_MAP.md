# Implementation Reality Map

## Legend
| Status | Definition |
| :--- | :--- |
| ✅ | **Confirmed Active**: Code exists, runs, and is integrated. |
| 🟡 | **Partial / Degraded**: Implemented but has limitations or bugs. |
| 🔴 | **Missing**: Architectural component defined but not found in code. |
| 🧪 | **Experimental / Mocked**: Exists as a test harness or hardcoded mock. |

---

## 1. Ingestion Layer
| Component | Sub-Component | Status | Notes |
| :--- | :--- | :--- | :--- |
| **NexusCompiler** | `compile_run` | ✅ | Core ingestion logic operational. |
| | `_llm_extract_pointers` | ✅ | LLM integration via `llm_client`. |
| | `_materialize_brick` | ✅ | Zero-trust validation (verbatim quote check) enforced. |
| **TreeSplitter** | `extract_message` | ✅ | Recursively extracts messages from conversation trees. |
| **BrickStore** | `get_brick_text` | 🟡 | Relies on file system (json) rather than DB for retrieval. |

## 2. Graph Layer
| Component | Sub-Component | Status | Notes |
| :--- | :--- | :--- | :--- |
| **GraphManager** | `register_node` | ✅ | Generic node storage (SQLite `nodes` table). |
| | `register_edge` | ✅ | Generic edge storage (SQLite `edges` table). |
| | `kill_node` | ✅ | Implements `KILLED` lifecycle state. |
| | `promote_node_to_frozen` | ✅ | Implements `FROZEN` state transition. |
| | `supersede_node` | ✅ | Handles `SUPERSEDED_BY` edges. |
| | `sync_bricks_to_nodes` | 🟡 | One-way sync from legacy `bricks` table to unified `nodes`. |
| | `validate_no_cycles` | ✅ | Cycle detection implemented in `validation.py`. |

## 3. Cognition Layer
| Component | Sub-Component | Status | Notes |
| :--- | :--- | :--- | :--- |
| **CortexAPI** | `route` | 🧪 | Hardcoded routing rules (keyword based). |
| | `generate` | ✅ | Calls `JarvisGateway` (Tier 2). |
| | `audit_trace` | ✅ | Logs usage to `phase3_audit_trace.jsonl`. |
| **JarvisGateway** | `pulse` (L1) | ✅ | Connects to local Ollama. |
| | `explain` (L2) | ✅ | Connects to Proxy (Claude). |
| | `synthesize` (L3) | ✅ | Connects to Proxy (o1/GPT-4). |
| **DSPy Modules** | `CognitiveExtractor` | ✅ | Fact/Diagram extraction implemented. |
| | `RelationshipSynthesizer` | ✅ | Relationship discovery implemented. |

## 4. Vector Layer
| Component | Sub-Component | Status | Notes |
| :--- | :--- | :--- | :--- |
| **VectorEmbedder** | `embed_query` | ✅ | Uses `sentence-transformers/all-MiniLM-L6-v2`. |
| | `_rewrite_with_llm` | ✅ | Optional GenAI query expansion. |
| **LocalVectorIndex** | `add_bricks` | ✅ | FAISS integration. |
| | `search` | ✅ | Standard K-NN search. |

## 5. UI Layer (Jarvis)
| Component | Sub-Component | Status | Notes |
| :--- | :--- | :--- | :--- |
| **React App** | `WallView` | ✅ | Visualizes nodes/bricks. |
| | `NodeEditor` | ✅ | Allows editing of node properties. |
| | `CortexVisualizer` | 🟡 | Visual component exists, integration depth unclear. |
| | `ControlStrip` | ✅ | Main navigation. |

---

## 6. Critical Gaps (Summary)
1.  **Orchestration**: No automated background job runner (e.g., Celery/Redis) to trigger `sync_bricks_to_nodes` or `validate_frozen_scope`. Currently appears to be script-driven.
2.  **Auth/Security**: No user authentication found in `api.py` or `server.py`. `user_id` is passed as a string argument.
3.  **Governance UI**: No dedicated UI workflow for "Promoting" or "Freezing" nodes found in `App.tsx` (though `GraphManager` supports it).
