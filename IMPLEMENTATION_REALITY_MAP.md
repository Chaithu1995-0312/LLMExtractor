# Implementation Reality Map

## 1. Backend: Cortex
| Component | Theoretical Role | Actual Implementation | Status |
|-----------|------------------|-----------------------|--------|
| **Server** | Production WSGI/ASGI | `Flask` running in `debug=True` mode on port 5001. | 🧪 Prototype |
| **API** | RESTful + Streaming | Standard REST endpoints (`/jarvis/*`). No streaming observed. | ✅ Functional |
| **State** | Stateless | Holds global instances of `BrickStore`, `CortexAPI`. | 🟡 Risk |

## 2. Core: Nexus
| Component | Theoretical Role | Actual Implementation | Status |
|-----------|------------------|-----------------------|--------|
| **Vector Store** | Pinecone/Milvus/Weaviate | `LocalVectorIndex` wrapping `faiss.IndexFlatL2`. | 🟡 Local Only |
| **Embeddings** | OpenAI/HuggingFace | `np.random.random` (Random noise). **Critical Gap.** | 🔴 MOCK |
| **Reranker** | Cross-Encoder/LLM | `RerankOrchestrator` placeholder logic (inferred). | 🟡 Incomplete |
| **Storage** | SQL/NoSQL | Flat JSON files (`output/nexus/bricks`, `nodes.json`). | 🧪 Prototype |
| **Walls** | Dynamic Context Windowing | `WallBuilder` concatenates text to MD files with token limits. | ✅ Functional |
| **Graph** | Dynamic Generation | Static `nodes.json` & `edges.json` read from disk. No builder found. | 🟡 Static |

## 3. Frontend: Jarvis
| Component | Theoretical Role | Actual Implementation | Status |
|-----------|------------------|-----------------------|--------|
| **Framework** | Modern Web App | React 18 + Vite + TypeScript. | ✅ Functional |
| **State Mgmt** | Redux/Context | Local `useState` in `App.tsx`. | 🟡 Simple |
| **Visualization**| Interactive Graph | Custom CSS/HTML rendering of nodes/edges (No D3/Cytoscape). | ✅ Custom |

## 4. Data Pipeline
| Component | Theoretical Role | Actual Implementation | Status |
|-----------|------------------|-----------------------|--------|
| **Ingest** | Streaming/API | Batch processing of `conversations.json` dump. | ✅ Batch |
| **Parsing** | Complex Tree Traversal | `TreeSplitter` flattens trees into linear paths. | ✅ Robust |
| **IDs** | UUIDs | Deterministic hashing (path hash, content hash). | ✅ Good |

## Status Legend
- ✅ **Functional**: Works as intended, production-grade logic.
- 🟡 **Partial/Risk**: Works but has limitations or tech debt.
- 🔴 **Broken/Mock**: Placeholder code, does not perform actual function.
- 🧪 **Prototype**: Functional but not scalable/robust.
