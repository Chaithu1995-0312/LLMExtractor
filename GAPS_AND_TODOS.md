# Gaps and TODOs

## 1. High Priority (Blockers)
| Status | Priority | Description | Impact |
| :--- | :--- | :--- | :--- |
| 🔴 | P0 | **Secure API Authentication** | No auth mechanism (JWT/Key) in `server.py`. Open access. |
| ✅ | P0 | **Background Job Runner** | Implemented Celery worker + Redis backend. `sync_bricks` and `assemble` are now async tasks. |
| ✅ | P1 | **BrickStore Database Integration** | `BrickStore` now queries `SyncDatabase` (SQLite) directly. |
| ✅ | P1 | **Graph Visualization** | `CortexVisualizer.tsx` rewritten with Cytoscape.js for scalable rendering. |

## 2. Medium Priority (Enhancements)
| Status | Priority | Description | Impact |
| :--- | :--- | :--- | :--- |
| ✅ | P2 | **L3 (Sage) Pipeline** | Enhanced `RelationshipSynthesizer` to fetch existing edges and prevent duplication. |
| 🔴 | P2 | **Conflict Resolution UI** | No UI workflow to resolve `CONFLICTS_WITH` edges manually. |
| ✅ | P2 | **Semantic Routing** | `CortexAPI.route` now uses embedding similarity (Cosine) against agent profiles. |

## 3. Low Priority (Future)
| Status | Priority | Description | Impact |
| :--- | :--- | :--- | :--- |
| 🔴 | P3 | **Multi-Tenant Scoping** | Current `ScopeNode` is global. Need user-specific scopes. |
| 🔴 | P3 | **Voice/Audio Input** | `JarvisGateway` supports text only. Audio ingestion planned for v4. |
| 🧪 | P3 | **Local LLM Fine-Tuning** | `NexusCompiler` could generate training data for a local Llama 3 model. |

## 4. Technical Debt
*   **Hardcoded Paths:** Many paths (e.g., `services/cortex/phase3_audit_trace.jsonl`) are relative and fragile.
*   **Duplicate Logic:** `SyncDatabase` and `GraphManager` both handle SQLite connections. Should share a connection pool.
*   **Testing:** `tests/` folder exists but coverage is unknown. `test_rewrite_integration.py` is one of few visible tests.
