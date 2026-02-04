# Implementation Reality Map

## Overview
This document maps the theoretical architectural components to their concrete implementation state.
Status Legend:
- ✅ **Complete**: Fully implemented and functional.
- 🟡 **Partial**: Implemented but missing features or robustness.
- 🔴 **Missing**: Planned but code does not exist.
- 🧪 **Experimental**: Prototype quality, not production-ready.

## Component Status

### 1. Ingestion Pipeline
| Component | File Path | Status | Notes |
|-----------|-----------|:------:|-------|
| **Sync Runner** | `src/nexus/sync/runner.py` | ✅ | Orchestrates the full pipeline successfully. |
| **Tree Splitter** | `src/nexus/extract/tree_splitter.py` | ✅ | Handles conversation splitting correctly. |
| **Brick Extractor** | `src/nexus/bricks/extractor.py` | ✅ | Fragments messages into bricks. |
| **Wall Builder** | `src/nexus/walls/builder.py` | ✅ | Aggregates bricks for storage. |

### 2. Vector System
| Component | File Path | Status | Notes |
|-----------|-----------|:------:|-------|
| **Local Index** | `src/nexus/vector/local_index.py` | ✅ | FAISS integration works. |
| **Embedder** | `src/nexus/vector/embedder.py` | ✅ | Singleton `sentence-transformers` wrapper. |
| **Brick Store** | `src/nexus/bricks/brick_store.py` | ✅ | Metadata retrieval works. |

### 3. Cognition Engine
| Component | File Path | Status | Notes |
|-----------|-----------|:------:|-------|
| **Assembler** | `src/nexus/cognition/assembler.py` | 🟡 | Works but has placeholder comments (`extracted_facts`, `decisions`). |
| **Recall** | `src/nexus/ask/recall.py` | ✅ | Integrates vector search + reranking. |
| **Reranker** | `src/nexus/rerank/orchestrator.py` | ✅ | Orchestrates cross-encoder reranking. |

### 4. Knowledge Graph
| Component | File Path | Status | Notes |
|-----------|-----------|:------:|-------|
| **Graph Manager** | `src/nexus/graph/manager.py` | 🟡 | Functional but naive JSON implementation (read/write entire file). |
| **Anchors** | `src/nexus/graph/anchors.override.json` | 🧪 | Mechanism exists but minimal logic usage. |

### 5. Service Layer
| Component | File Path | Status | Notes |
|-----------|-----------|:------:|-------|
| **Cortex Server** | `services/cortex/server.py` | ✅ | Flask API exposing required endpoints. |
| **Cortex API** | `services/cortex/api.py` | 🟡 | Helper class, possibly redundant with server logic. |

## Reality Gaps
1. **Concurrency**: The GraphManager and Index writing are not thread-safe.
2. **Error Handling**: Many `try/except Exception` blocks that swallow errors or print to stdout.
3. **Hardcoded Paths**: `DEFAULT_OUTPUT_DIR` and other paths rely on relative positioning rather than robust configuration injection.
4. **Testing**: `tests/` directory exists but coverage is unknown; `test_assemble_topic.py` is a script, not a proper test suite.
