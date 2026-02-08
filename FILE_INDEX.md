# NEXUS FILE INDEX

## 1. Graph Layer (`src/nexus/graph/`)
- `manager.py`: Primary interface for graph state.
    - `GraphManager`: Transactional node/edge persistence and lifecycle control.
- `schema.py`: Data models for Graph entities.
    - `Intent`, `Source`, `ScopeNode`, `Edge`: Core structural definitions.
- `projection.py`: Logic for projecting graph state into specific views (e.g., Walls).
- `prompt_manager.py`: Manages system prompts and governance rules.
    - `PromptManager`: CRUD for versioned AI instructions.
- `validation.py`: Structural integrity checks (cycles, orphans).

## 2. Cognition Layer (`src/nexus/cognition/`)
- `assembler.py`: High-level orchestration of topic assembly.
    - `assemble_topic`: Fetches context and triggers cognitive extraction.
- `dspy_modules.py`: DSPy signatures and modules for AI reasoning.
    - `CognitiveExtractor`: Transforms raw text into structured facts.
    - `RelationshipSynthesizer`: Infers logical edges between existing intents.
- `synthesizer.py`: Batch processing for relationship discovery.

## 3. Ingestion & Sync Layer (`src/nexus/sync/`, `src/nexus/extract/`)
- `compiler.py`: The logic for turning raw JSON/Text into Bricks.
    - `NexusCompiler`: Path resolution, pointer extraction, and brick materialization.
- `db.py`: Persistence for the synchronization process.
    - `SyncDatabase`: Tracks topics, runs, and brick fingerprints.
- `ingest_history.py`: Legacy ingestion tools for historical data.
- `tree_splitter.py`: Decomposes large JSON exports into traversable trees.

## 4. Vector & Recall Layer (`src/nexus/vector/`, `src/nexus/ask/`, `src/nexus/rerank/`)
- `embedder.py`: Query and text vectorization.
    - `VectorEmbedder`: Singleton for embedding generation and query rewriting.
- `local_index.py`: FAISS-based vector storage.
    - `LocalVectorIndex`: High-speed semantic search implementation.
- `recall.py`: Top-level retrieval functions.
    - `recall_bricks`: Retrieves and reranks candidates based on query.
- `orchestrator.py` (rerank): Multi-strategy reranking.
    - `RerankOrchestrator`: Sequences LLM and heuristic ranking passes.

## 5. Bricks Layer (`src/nexus/bricks/`)
- `brick_store.py`: Read-optimized access to atomic data.
    - `BrickStore`: Fast retrieval of brick text and metadata.
- `extractor.py`: Utility for generating brick IDs and extracting atoms.

## 6. Service Layer (`services/cortex/`)
- `api.py`: Business logic for the Cortex system.
    - `CortexAPI`: Orchestrates recall, generation, and auditing.
- `gateway.py`: Proxy interface for external model interaction.
    - `JarvisGateway`: Managed access to local or remote LLM providers.
- `server.py`: FastAPI endpoints for UI and external integration.
- `tasks.py`: Background job definitions for async processing.

## 7. UI Layer (`ui/jarvis/`)
- `src/App.tsx`: Main application container.
- `src/store.ts`: Client-side state management (Zustand).
- `src/components/`: Modular UI units (AuditPanel, WallView, NodeEditor).
