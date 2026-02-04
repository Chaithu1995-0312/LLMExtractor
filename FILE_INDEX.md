# File Index

## Configuration & Meta
| File | Status | Description |
|------|:------:|-------------|
| `pyproject.toml` | ✅ | Project dependencies and build config. |
| `.gitignore` | ✅ | Git ignore rules. |
| `README.md` | ✅ | General project entry point. |

## Source: Nexus Core (`src/nexus`)

### Sync & Ingestion
| File | Status | Description |
|------|:------:|-------------|
| `src/nexus/sync/__main__.py` | ✅ | CLI entry point for sync. |
| `src/nexus/sync/runner.py` | ✅ | Orchestrates loading, extraction, wall building, and indexing. |
| `src/nexus/extract/tree_splitter.py` | ✅ | Splits huge JSON into conversation trees. |
| `src/nexus/bricks/extractor.py` | ✅ | Fragments text into bricks. |
| `src/nexus/bricks/brick_store.py` | ✅ | Utility to read brick text/metadata from disk. |
| `src/nexus/walls/builder.py` | ✅ | Aggregates processed files into walls. |

### Vector & Search
| File | Status | Description |
|------|:------:|-------------|
| `src/nexus/vector/local_index.py` | ✅ | FAISS wrapper for adding/searching embeddings. |
| `src/nexus/vector/embedder.py` | ✅ | SentenceTransformers wrapper (Singleton). |
| `src/nexus/ask/recall.py` | ✅ | Recalls bricks and applies reranking. |

### Reranking
| File | Status | Description |
|------|:------:|-------------|
| `src/nexus/rerank/orchestrator.py` | ✅ | Manages reranking logic. |
| `src/nexus/rerank/cross_encoder.py` | ✅ | CrossEncoder model wrapper. |
| `src/nexus/rerank/llm_reranker.py` | 🧪 | LLM-based reranking implementation. |
| `src/nexus/rerank/heuristic.py` | 🧪 | Heuristic-based reranking. |

### Cognition & Graph
| File | Status | Description |
|------|:------:|-------------|
| `src/nexus/cognition/assembler.py` | 🟡 | Assembles Topics from recalled bricks. |
| `src/nexus/graph/manager.py` | 🟡 | JSON Graph DB manager (No concurrency control). |
| `src/nexus/graph/nodes.json` | ✅ | Persistent node storage. |
| `src/nexus/graph/edges.json` | ✅ | Persistent edge storage. |

### CLI
| File | Status | Description |
|------|:------:|-------------|
| `src/nexus/cli/main.py` | ✅ | Main CLI dispatcher. |
| `src/nexus/config.py` | ✅ | Central configuration (paths/constants). |

## Services: Cortex (`services/cortex`)
| File | Status | Description |
|------|:------:|-------------|
| `services/cortex/server.py` | ✅ | Flask API server. |
| `services/cortex/api.py` | 🟡 | API logic helper (redundant?). |

## Scripts (`scripts/`)
| File | Status | Description |
|------|:------:|-------------|
| `scripts/test_assemble_topic.py` | 🧪 | Test script for assembly logic. |
| `scripts/build_index.py` | 🟡 | Standalone index builder. |
| `scripts/extract_prompts.py` | 🧪 | Utility to extract prompts. |

## UI (`ui/`)
| File | Status | Description |
|------|:------:|-------------|
| `ui/jarvis/` | ✅ | React/Vite frontend for Jarvis. |
| `ui/app.js` | 🔴 | Legacy/Deprecated UI file? |
| `ui/index.html` | 🔴 | Legacy/Deprecated UI file? |
