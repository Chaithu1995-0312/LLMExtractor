# IMPLEMENTATION_REALITY_MAP

This document maps the implementation status of the NEXUS architecture.

## 1. System-Wide Layer Status
| Layer | Status | Primary Authority |
| :--- | :--- | :--- |
| Ingestion | ✅ | `NexusIngestor` |
| Graph | ✅ | `GraphManager` |
| Vector | ✅ | `LocalVectorIndex` |
| Cognition | 🟡 | `CognitiveExtractor` (In-Progress Refinement) |
| Service | ✅ | `CortexAPI` |
| UI | 🟡 | `WallView` (Partial Interactive Controls) |

## 2. Method-Level Reality

### 2.1 Graph Layer (`src/nexus/graph`)
| Class | Method | Status | Notes |
| :--- | :--- | :--- | :--- |
| `GraphManager` | `register_node` | ✅ | Full SQLite persistence |
| `GraphManager` | `register_edge` | ✅ | Supports multi-typed relationships |
| `GraphManager` | `promote_node_to_frozen` | ✅ | Enforces lifecycle transitions |
| `GraphManager` | `supersede_node` | ✅ | Manages version history / replacements |
| `GraphManager` | `kill_node` | ✅ | Soft-delete with tombstone reasoning |
| `GraphManager` | `_log_audit_event` | ✅ | Internal persistence logging |

### 2.2 Cognition Layer (`src/nexus/cognition`)
| Class | Method | Status | Notes |
| :--- | :--- | :--- | :--- |
| `CognitiveExtractor` | `forward` | ✅ | DSPy implementation |
| `CognitiveExtractor` | `extract_facts` | 🧪 | Mocked via FactSignature |
| `CognitiveExtractor` | `generate_diagram` | 🧪 | Mocked via DiagramSignature |
| `Assembler` | `assemble_topic` | 🟡 | Implemented but lacks robust conflict resolution |

### 2.3 Service Layer (`services/cortex`)
| Class | Method | Status | Notes |
| :--- | :--- | :--- | :--- |
| `CortexAPI` | `route` | ✅ | Main decision logic for queries |
| `CortexAPI` | `generate` | ✅ | Multi-brick context assembly |
| `CortexAPI` | `_audit_trace` | ✅ | JSONL logging implementation |
| `Orchestration` | `verifier_node` | 🔴 | Planned for Phase 4 quality checks |
| `Orchestration` | `self_correction_node` | 🔴 | Planned for Phase 4 feedback loops |

### 2.4 Vector Layer (`src/nexus/vector`)
| Class | Method | Status | Notes |
| :--- | :--- | :--- | :--- |
| `VectorEmbedder` | `embed_query` | ✅ | HuggingFace integration |
| `VectorEmbedder` | `_rewrite_with_llm` | ✅ | Query expansion logic |
| `LocalVectorIndex` | `search` | ✅ | FAISS k-NN search |

### 2.5 Ingestion Layer (`src/nexus/sync`)
| Class | Method | Status | Notes |
| :--- | :--- | :--- | :--- |
| `NexusIngestor` | `brickify` | ✅ | Atomization logic |
| `NexusIngestor` | `ingest_history` | ✅ | Batch processing loop |

## 3. Layer Interactions Status
| Source Layer | Target Layer | Status | Flow Type |
| :--- | :--- | :--- | :--- |
| Ingestion | Vector | ✅ | Direct Embedding push |
| Ingestion | Graph | ✅ | Node/Source registration |
| Service | Graph | ✅ | Read/Write (Lifecycle) |
| Service | Cognition | 🟡 | Sync call, lacks async worker queue |
| UI | Service | ✅ | REST API |
