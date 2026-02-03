# MODULE_DEEP_DIVES.md

## 1. `src/nexus/vector/embedder.py` (VectorEmbedder)

### 1.1. Purpose

Provides a singleton interface for embedding text (queries or document chunks) into fixed-size numerical vectors using a pre-trained `SentenceTransformer` model. This is a foundational component for semantic search and similarity calculations within Nexus.

### 1.2. Key Components & Logic

- **`VectorEmbedder` Class:** Implements the singleton pattern to ensure only one instance of the embedding model is loaded into memory.
- **`_get_model()` Method:**
    - Lazily loads the `all-MiniLM-L6-v2` `SentenceTransformer` model upon first request.
    - This model outputs 384-dimensional embeddings.
    - Includes error handling for `ImportError` (if `sentence-transformers` is not installed) and general exceptions during model loading.
- **`embed_query(query: str) -> np.ndarray`:**
    - Takes a single string query.
    - Encodes it using the loaded `SentenceTransformer` model.
    - Returns a 1x384 NumPy array of `float32` representing the query embedding.
- **`embed_texts(texts: List[str]) -> np.ndarray`:**
    - Takes a list of strings (e.g., brick content).
    - Encodes them in a batch using the `SentenceTransformer` model.
    - Returns an Nx384 NumPy array of `float32`, where N is the number of texts.
- **`get_embedder()` Function:** A global accessor to retrieve the singleton `VectorEmbedder` instance.

### 1.3. Dependencies

- `numpy` (for array manipulation).
- `sentence_transformers` (primary external dependency for the embedding model).

### 1.4. Invariants & Assumptions

- **Singleton:** Only one instance of `VectorEmbedder` (and thus one embedding model) will exist at runtime.
- **Fixed Model:** The `all-MiniLM-L6-v2` model is hardcoded.
- **Fixed Dimension:** Output embeddings will always be 384 dimensions.
- **Float32 Output:** Embeddings are cast to `float32` for compatibility (e.g., with FAISS).

## 2. `src/nexus/vector/local_index.py` (LocalVectorIndex)

### 2.1. Purpose

Manages a local FAISS index for efficient storage and similarity search of vector embeddings. It serves as the primary mechanism for quickly retrieving relevant "bricks" based on a query's semantic similarity.

### 2.2. Key Components & Logic

- **`LocalVectorIndex` Class:**
    - **Initialization (`__init__`)**: 
        - Sets up file paths for the FAISS index (`data/index/index.faiss`) and brick ID metadata (`data/brick_ids.json`) using `nexus.config`.
        - Initializes an empty `faiss.IndexFlatL2` with a fixed dimension of 384.
        - Attempts to load an existing index and brick IDs if files are present.
    - **`load()` Method:**
        - Reads the FAISS index from `index.faiss`.
        - Loads the corresponding list of `brick_id`s from `brick_ids.json`.
    - **`save()` Method:**
        - Creates necessary parent directories.
        - Writes the current FAISS index to `index.faiss`.
        - Dumps the list of `brick_id`s to `brick_ids.json`.
    - **`add_bricks(bricks: List[Dict])` Method:**
        - Filters for bricks with `status == "PENDING"`.
        - Extracts `content` from pending bricks.
        - Uses the `VectorEmbedder` singleton (`get_embedder()`) to generate embeddings for these texts.
        - Adds the new embeddings to the FAISS index (`self.index.add(embeddings)`).
        - Appends corresponding `brick_id`s to `self.brick_ids`.
        - Updates the `status` of processed bricks to `"EMBEDDED"`.
    - **`search(query_vector: np.ndarray, k: int = 5)` Method:**
        - Performs a k-nearest neighbor search on the FAISS index using the provided `query_vector`.
        - Returns a tuple of distances and corresponding indices from the FAISS index. Handles empty index gracefully.

### 2.3. Dependencies

- `pathlib` (for path manipulation).
- `json` (for serializing/deserializing brick IDs).
- `numpy` (for vector operations).
- `faiss` (core dependency for the vector index).
- `nexus.config` (for path constants).
- `nexus.vector.embedder` (for obtaining the `VectorEmbedder` singleton).

### 2.4. Invariants & Assumptions

- **Fixed Dimension:** The FAISS index is initialized with a dimension of 384, matching the `VectorEmbedder` output.
- **L2 Distance:** Uses `IndexFlatL2`, implying Euclidean (L2) distance for similarity measurement.
- **Persistence:** The index state and brick ID mapping are persisted to disk and loaded on initialization.
- **Brick Status:** Only bricks with `"PENDING"` status are added to the index; their status is updated to `"EMBEDDED"` after processing.
- **Mapping Consistency:** The order of `brick_id`s in `self.brick_ids` must correspond exactly to the order of vectors in the `faiss.Index` for correct retrieval.

## 3. `src/nexus/bricks/brick_store.py` (BrickStore)

### 3.1. Purpose

Provides a centralized mechanism to access and retrieve metadata and raw text content of individual "bricks" stored as JSON files. It acts as the canonical source for brick data once extracted and stored.

### 3.2. Key Components & Logic

- **`BrickStore` Class:**
    - **Initialization (`__init__`)**: 
        - Determines the `bricks_dir` (defaults to `output/nexus/bricks` based on `nexus.config.DATA_DIR`'s parent directory).
        - Initializes an empty `metadata_store` dictionary.
        - Calls `_load_all_bricks_metadata()` to populate the store.
    - **`_load_all_bricks_metadata()` Method:**
        - Walks through the `bricks_dir` to find all `.json` files.
        - For each JSON file, it attempts to load a list of brick dictionaries.
        - For each brick, it stores its `source_file`, `source_span`, and the `file_path` where it was found, keyed by `brick_id` in `self.metadata_store`.
        - Designed to be a simple mock/initial loader for metadata.
    - **`get_brick_metadata(brick_id: str) -> Optional[Dict]`:**
        - Retrieves the metadata dictionary for a given `brick_id` from `self.metadata_store`.
    - **`get_brick_text(brick_id: str) -> Optional[str]`:**
        - First retrieves the brick's metadata to find its `file_path`.
        - Opens the identified JSON file.
        - Iterates through the JSON file to find the specific brick by `brick_id`.
        - Returns the `content` field of that brick. Returns `None` if not found or on error.
        - Enforces "MODE-1 Violation" logging if a brick cannot be reloaded (critical for `CortexAPI`'s secure generation).

### 3.3. Dependencies

- `json` (for reading brick JSON files).
- `os` (for path manipulation).
- `nexus.config` (for deriving default `bricks_dir`).

### 3.4. Invariants & Assumptions

- **Brick Storage Format:** Bricks are expected to be stored as a list of dictionaries within JSON files, each with at least `brick_id`, `content`, `source_file`, and `source_span` fields.
- **Directory Structure:** Bricks are expected to reside in `output/nexus/bricks/` (or a configured alternative).
- **Metadata Caching:** Brick metadata (paths, source info) is loaded once on `BrickStore` initialization. Text content is loaded on demand.
- **MODE-1 Enforcement:** Critical logging occurs if `get_brick_text` fails, highlighting a potential security/consistency issue.

## 4. `src/nexus/ask/recall.py` (Semantic Recall Logic)

### 4.1. Purpose

Provides the core semantic search functionality for Nexus, allowing queries to be matched against stored bricks using vector similarity and a multi-stage reranking pipeline. It's the central entry point for retrieving relevant information.

### 4.2. Key Components & Logic

- **Global Initializations:** 
    - `_local_index = LocalVectorIndex()`: Initializes the FAISS vector index.
    - `_brick_store = BrickStore()`: Initializes the brick content store.
    - `_reranker = RerankOrchestrator()`: Initializes the reranking pipeline.
    - These are initialized globally for simplicity, implying they are singletons or long-lived.
- **`_normalize_distance_to_confidence(distance: float) -> float`:**
    - Converts raw FAISS L2 distances into a 0.0-1.0 confidence score. A simple linear mapping is used where 0 distance (perfect match) is 1.0 confidence, and 2.0 distance (max for normalized vectors) is 0.0 confidence.
- **`recall_bricks(query: str, k: int = 10) -> List[Dict]`:**
    - Main recall function.
    - Gets the `VectorEmbedder` singleton and embeds the `query`.
    - Performs an initial vector search using `_local_index.search()` to get `k` candidate `brick_id`s and raw distances.
    - Converts distances to `base_confidence` scores.
    - Hydrates candidates with `brick_text` from `_brick_store.get_brick_text()` (essential for reranking).
    - Passes the `query` and hydrated `candidates` to `_reranker.rerank()`.
    - Formats the final results to include `brick_id`, `confidence` (final score from reranker), and `reranker_used`.
- **`recall_bricks_readonly(query: str, k: int = 10) -> List[Dict]`:**
    - A wrapper around `recall_bricks`, explicitly intended for read-only preview scenarios (e.g., by `CortexAPI.ask_preview`).
    - Designed to prevent accidental side-effects or audit logging from preview calls.
    - Dynamically appends `nexus-cli` to `sys.path` to resolve imports, indicating a potential deployment/packaging challenge.
- **`get_recall_brick_metadata(brick_id: str) -> Dict | None`:**
    - Retrieves metadata for a specific brick using `_brick_store.get_brick_metadata()`.

### 4.3. Dependencies

- `nexus.vector.local_index`
- `nexus.bricks.brick_store`
- `nexus.vector.embedder`
- `nexus.rerank.orchestrator`
- `os`, `sys` (for path manipulation and import hacks in `recall_bricks_readonly`).

### 4.4. Invariants & Assumptions

- **Global State:** `_local_index`, `_brick_store`, and `_reranker` are initialized once at module load time, implying a shared, persistent state for the recall functionality.
- **Distance Normalization:** Assumes L2 distances from FAISS are normalized to a consistent range (0-2 for normalized vectors) to allow for a meaningful confidence conversion.
- **Reranker Output:** Expects the reranker to return a list of dictionaries with `final_score` and `reranker_used` fields.
- **Read-Only Enforcement:** The `_readonly` variant is a convention; actual read-only nature depends on underlying component implementations (e.g., `BrickStore.get_brick_text` is read-only).
- **Circular Import Handling:** The `sys.path` manipulation in `recall_bricks_readonly` is a workaround for potential circular dependencies or module visibility issues in a complex package structure.

## 5. `src/nexus/rerank/orchestrator.py` (RerankOrchestrator)

### 5.1. Purpose

Manages a tiered reranking pipeline for search candidates, providing a robust and fault-tolerant mechanism to refine initial vector search results. It attempts more sophisticated reranking methods first, falling back to simpler ones if failures occur.

### 5.2. Key Components & Logic

- **`RerankOrchestrator` Class:**
    - **Initialization (`__init__`)**: 
        - Initializes `primary` (LLM), `secondary` (CrossEncoder), and `tertiary` (Heuristic) rerankers.
        - Attempts to load `LlmReranker` and `CrossEncoderReranker`. If these fail (e.g., due to missing dependencies or models), they are gracefully set to `None`, allowing for dynamic fallback. `HeuristicReranker` is always initialized as it has no external dependencies.
    - **`rerank(query: str, candidates: List[Dict]) -> List[Dict]`:**
        - Main entry point for reranking.
        - If no candidates, returns an empty list.
        - **Primary Attempt (LLM):** If `self.primary` exists, attempts to call `self.primary.rank()`. If successful, returns its results.
        - **Secondary Attempt (CrossEncoder):** If the primary fails or is `None` and `self.secondary` exists, attempts `self.secondary.rank()`. If successful, returns its results.
        - **Tertiary Fallback (Heuristic):** If both primary and secondary fail or are `None`, it defaults to `self.tertiary.rank()` (which is guaranteed to exist).
        - Includes `try-except` blocks for each reranker stage to ensure graceful fallback on operational errors.

### 5.3. Dependencies

- `nexus.rerank.llm_reranker` (for `LlmReranker`)
- `nexus.rerank.cross_encoder` (for `CrossEncoderReranker`)
- `nexus.rerank.heuristic` (for `HeuristicReranker`)

### 5.4. Invariants & Assumptions

- **Tiered Fallback:** The reranking pipeline strictly follows the order: LLM -> CrossEncoder -> Heuristic.
- **Graceful Degradation:** The system is designed to function even if advanced rerankers (LLM, CrossEncoder) are unavailable, falling back to the basic heuristic.
- **Consistent Interface:** All individual rerankers (`LlmReranker`, `CrossEncoderReranker`, `HeuristicReranker`) are assumed to expose a `rank(query, candidates)` method that returns a list of dictionaries with `final_score` and `reranker_used`.
- **Deterministic Fallback:** The choice of reranker is deterministic based on availability and successful execution.

## 6. `src/nexus/rerank/llm_reranker.py` (LlmReranker)

### 6.1. Purpose

Implements a high-fidelity reranking strategy using a local, quantized Large Language Model (LLM). This component provides fine-grained relevance scoring by leveraging the LLM's understanding of query and context.

### 6.2. Key Components & Logic

- **`LlmReranker` Class:**
    - **Initialization (`__init__`)**: 
        - Expects a `model_path` (defaulting to `models/llama-3-8b-quantized.gguf`).
        - Checks for the model file's existence; raises `FileNotFoundError` if missing.
        - Attempts to initialize `llama_cpp.Llama` with the specified model, `n_ctx` (context window size), and `seed` for deterministic output.
        - Raises `ImportError` if `llama-cpp-python` is not installed or `RuntimeError` if LLM loading fails.
    - **`rank(query: str, candidates: List[Dict]) -> List[Dict]`:**
        - Iterates through each `candidate` brick.
        - Constructs a prompt for the LLM, including the `query` and the `brick_text` (truncated to 800 characters to fit within typical LLM context windows).
        - Calls the local LLM (`self.llm`) to generate a relevance score (0.0-1.0).
        - Extracts the numerical score from the LLM's text output using regex, handling potential parsing errors by defaulting to 0.0.
        - Assigns the clamped `final_score` (between 0.0 and 1.0) and `reranker_used: "llm_reranker"` to each candidate.
        - Sorts the entire `candidates` list by `final_score` in descending order.

### 6.3. Dependencies

- `llama-cpp-python` (primary external dependency for local LLM inference).
- `os` (for checking model file existence).
- `re` (for parsing LLM output).

### 6.4. Invariants & Assumptions

- **Local LLM Required:** This reranker *requires* a local, `llama-cpp-python`-compatible LLM model file to be present at the configured path.
- **Deterministic Output:** `seed=42` and `temperature=0.0` are set for the LLM call to ensure consistent scoring for the same inputs.
- **Prompt Format:** The LLM prompt is structured to elicit a numerical relevance score (0.0-1.0).
- **Truncation:** Brick text is truncated to 800 characters to prevent context window overflow with the LLM.
- **Score Range:** Final scores are clamped to be between 0.0 and 1.0.

## 7. `src/nexus/rerank/cross_encoder.py` (CrossEncoderReranker)

### 7.1. Purpose

Provides a mid-tier reranking strategy using a `sentence-transformers` CrossEncoder model. It offers more nuanced relevance assessment than simple heuristics but is generally faster and less resource-intensive than a full LLM.

### 7.2. Key Components & Logic

- **`CrossEncoderReranker` Class:**
    - **Initialization (`__init__`)**: 
        - Attempts to load the `cross-encoder/ms-marco-TinyBERT-L-2-v2` `CrossEncoder` model from `sentence-transformers`.
        - Sets `torch.manual_seed(42)` for deterministic behavior (assuming a GPU is not used or determinism is enforced).
        - Raises `ImportError` if `sentence-transformers` or `torch` are not installed or `RuntimeError` if model loading fails.
    - **`rank(query: str, candidates: List[Dict]) -> List[Dict]`:**
        - If no candidates, returns an empty list.
        - Creates `pairs` of `[query, brick_text]` for the CrossEncoder model.
        - Calls `self.model.predict()` to get raw relevance scores for all pairs in a batch.
        - **Score Normalization:** Normalizes the raw scores to a 0.0-1.0 range using Min-Max scaling across the current batch of candidates. This ensures consistency with other rerankers' output.
        - Assigns the normalized `final_score` and `reranker_used: "cross_encoder"` to each candidate.
        - Sorts the entire `candidates` list by `final_score` in descending order.

### 7.3. Dependencies

- `sentence_transformers` (primary external dependency).
- `torch` (underlying dependency for `sentence-transformers`).
- `numpy` (for handling scores array).

### 7.4. Invariants & Assumptions

- **CrossEncoder Model Required:** This reranker *requires* the `cross-encoder/ms-marco-TinyBERT-L-2-v2` model to be available via `sentence-transformers`.
- **Deterministic Scoring:** `torch.manual_seed(42)` is set for consistency.
- **Batch Processing:** `model.predict` is used for efficient batch inference.
- **Min-Max Normalization:** Scores are normalized within the current batch, which means the absolute score of a brick might vary between different reranking calls depending on other candidates present. The relative ranking within a call remains consistent.
- **Score Range:** Final scores are clamped to be between 0.0 and 1.0.

## 8. `src/nexus/rerank/heuristic.py` (HeuristicReranker)

### 8.1. Purpose

Provides a basic, dependency-free, and always-available fallback reranking strategy. It uses simple lexical heuristics to reorder candidates when more advanced LLM or CrossEncoder rerankers are unavailable or fail.

### 8.2. Key Components & Logic

- **`HeuristicReranker` Class:**
    - **Initialization (`__init__`)**: Simple constructor; no external models or complex setup.
    - **`rank(query: str, candidates: List[Dict]) -> List[Dict]`:**
        - If no candidates, returns an empty list.
        - Converts the `query` into a set of lowercase tokens.
        - For each `candidate` brick:
            - Initializes a `score` to 0.0.
            - **Token Overlap (0.5 weight):** Calculates the intersection of query tokens and brick text tokens. Normalizes this by the number of query tokens and adds to the `score`.
            - **Exact Phrase Match (0.4 weight):** Adds a significant boost if the exact lowercase query string is found within the brick text.
            - **Base Confidence Preservation (0.1 weight):** Adds a small fraction of the `base_confidence` (from the initial vector search) to the score, preserving some original signal.
            - Clamps the final calculated `score` to be between 0.0 and 1.0.
            - Assigns this as `final_score` and `reranker_used: "heuristic"`.
        - Sorts the entire `candidates` list by `final_score` in descending order.

### 8.3. Dependencies

- `re` (for tokenizing text).

### 8.4. Invariants & Assumptions

- **No External Dependencies:** This reranker is guaranteed to always function, making it a robust fallback.
- **Lexical Matching:** Relies solely on text content and token matching, not semantic understanding.
- **Fixed Weights:** The weights for token overlap, exact phrase match, and base confidence are hardcoded.
- **Score Range:** Final scores are clamped to be between 0.0 and 1.0.
- **Query Tokenization:** Simple `re.findall(r'\w+')` is used for tokenization.

## 9. `services/cortex/api.py` (CortexAPI)

### 9.1. Purpose

Exposes the core functionalities of the Nexus system (semantic search, content generation) as a microservice API. It provides intent-based routing, secure LLM generation with memory injection, and mandatory audit logging.

### 9.2. Key Components & Logic

- **`CortexAPI` Class:**
    - **Initialization (`__init__`)**: 
        - Takes an optional `audit_log_path` (defaults to `phase3_audit_trace.jsonl`).
        - Initializes a `BrickStore` instance.
    - **`route(user_query: str) -> Dict`:**
        - Endpoint: `/route`.
        - Implements deterministic intent-based routing based on keywords in the `user_query` (case-insensitive).
        - Hardcoded rules map keywords to `agent_id` (e.g., "Jarvis", "Architect") and `model` (e.g., "Claude", "Gemini", "GPT").
        - Provides a default fallback agent/model if no specific intent is matched.
        - This is a "LOCKED Rules" component, implying immutability of routing logic.
    - **`generate(user_id: str, agent_id: str, user_query: str, brick_ids: List[str]) -> Dict`:**
        - Endpoint: `/generate`.
        - Handles secure LLM-based content generation.
        - **MODE-1 Enforcement:** Calls `_reload_source_text(brick_ids)` to retrieve the raw content of all specified bricks. If `_reload_source_text` returns an empty string (indicating a failure to reload any brick), generation is blocked with a "MODE-1 Violation" error.
        - **LLM Call:** 
            - Constructs a `prompt` using the reloaded `context_text` and `user_query`.
            - Prioritizes OpenAI (`gpt-4o`) if `OPENAI_API_KEY` is available.
            - Falls back to a local Ollama instance (`llama3` at `http://localhost:11434/api/generate`) via `requests` if OpenAI key is not found or fails.
            - Provides a final mock fallback response if no LLM is available.
            - Records `model` and `token_cost` (estimated for OpenAI, default for others).
        - **Audit Record:** Calls `_audit_trace()` to log the generation event to `phase3_audit_trace.jsonl`.
        - Returns the generated `response`, `model` used, and `status`.
    - **`ask_preview(query: str) -> Dict`:**
        - Endpoint: `/ask_preview`.
        - Provides a read-only preview of recalled bricks for the Jarvis UI.
        - **CRITICAL:** Explicitly states that it *MUST NOT* call `self.generate()` or emit audit rows.
        - Calls `nexus.ask.recall.recall_bricks_readonly(query)` to get top bricks.
        - Formats the output to include `brick_id` and `confidence`.
        - Includes a `sys.path` append to resolve `nexus.ask.recall` import, indicating an external dependency loading pattern.
    - **`_reload_source_text(self, brick_ids: List[str]) -> str`:**
        - Internal "MODE-1 enforcement layer".
        - Iterates through `brick_ids`, retrieving raw text for each from `self.brick_store.get_brick_text()`.
        - Fails fast (returns empty string) if any brick fails to reload, printing a critical warning.
        - Concatenates all successfully reloaded texts.
    - **`_audit_trace(self, user_id: str, agent_id: str, brick_ids: List[str], model: str, token_cost: float)`:**
        - Internal mandatory audit logging function.
        - Creates a JSON record with details of the generation event.
        - Appends the JSON record to the configured `audit_log_path`.

### 9.3. Dependencies

- `json` (for audit logging).
- `os`, `sys` (for path manipulation, environment variables, and import hacks).
- `datetime`, `timezone` (for timestamps in audit logs).
- `nexus.bricks.brick_store.BrickStore` (for brick content retrieval).
- `openai` (conditional import if `OPENAI_API_KEY` is set).
- `requests` (conditional import for Ollama interaction).
- `nexus.ask.recall.recall_bricks_readonly` (for preview functionality).

### 9.4. Invariants & Assumptions

- **Mandatory Audit:** All `/generate` calls *must* result in an audit record being logged.
- **MODE-1 Secure Generation:** Raw source text for all provided `brick_ids` must be successfully reloaded at the time of generation; otherwise, the request is blocked.
- **Deterministic Routing:** The `/route` endpoint uses hardcoded, unchangeable rules.
- **LLM Fallback Order:** OpenAI (API) -> Ollama (local) -> Mock (fallback).
- **Read-Only Preview:** `/ask_preview` is strictly read-only and has no side effects (no generation, no audit).
- **External Nexus Import:** `CortexAPI` directly imports `recall_bricks_readonly` from `nexus.ask.recall`, signifying its reliance on core Nexus functionalities.
- **`OPENAI_API_KEY`:** Assumed to be available as an environment variable for OpenAI integration.
- **Ollama Endpoint:** Assumes a local Ollama instance runs on `http://localhost:11434`.

## 10. `src/nexus/cli/main.py` (CLI Main Entry Point)

### 10.1. Purpose

Serves as the command-line interface for the Nexus system, allowing users and scripts to interact with its core functionalities, potentially including synchronization, index building, and basic queries.

### 10.2. Key Components & Logic

- **`main()` Function:** (🟡 UNCONFIRMED - The actual implementation of `main` was not reviewed, but its definition in `pyproject.toml` as `nexus.cli.main:main` confirms it as the CLI entry point.)
- **`pyproject.toml` Entry:** The `[project.scripts]` section maps the `nexus` command directly to this `main` function.

### 10.3. Dependencies

- (🟡 UNCONFIRMED - Dependencies would depend on the specific CLI commands implemented, but would likely include other Nexus modules like `nexus.sync`, `nexus.ask`, etc.)

### 10.4. Invariants & Assumptions

- **CLI Entry Point:** This file is the official entry point for all command-line interactions with Nexus.
- **Setuptools Integration:** Relies on `setuptools` to create the `nexus` executable from this file.

## 11. `src/nexus/sync/__main__.py` (Synchronization Main Entry Point)

### 11.1. Purpose

(🟡 UNCONFIRMED - Inferred to be the primary entry point for executing content synchronization and index building operations within the Nexus system, typically run as a module via `python -m nexus.sync`.)

### 11.2. Key Components & Logic

- (🟡 UNCONFIRMED - Specific logic would likely involve invoking `nexus.sync.runner` and potentially other extraction, embedding, and indexing components.)

### 11.3. Dependencies

- (🟡 UNCONFIRMED - Likely depends on `nexus.sync.runner` and other Nexus modules involved in content processing.)

### 11.4. Invariants & Assumptions

- **Module Execution:** Designed to be run as a top-level module.
- **Synchronization Orchestration:** Assumed to trigger the full content ingestion pipeline.

## 12. `src/nexus/sync/runner.py` (Synchronization Orchestrator)

### 12.1. Purpose

(🟡 UNCONFIRMED - Inferred to orchestrate the end-to-end process of content synchronization, including steps like extracting content into bricks, embedding them, and adding them to the vector index.)

### 12.2. Key Components & Logic

- (🟡 UNCONFIRMED - Would likely contain a main `run()` function or similar, coordinating calls to `nexus.bricks.extractor`, `nexus.vector.embedder`, and `nexus.vector.local_index`.)

### 12.3. Dependencies

- (🟡 UNCONFIRMED - Expected dependencies include `nexus.bricks.extractor`, `nexus.vector.embedder`, `nexus.vector.local_index`, and potentially `nexus.config`.)

### 12.4. Invariants & Assumptions

- **Sequential Processing:** Assumed to execute content ingestion steps in a defined order.
- **Error Handling:** Should include robust error handling for various stages of the synchronization process.

## 13. `services/cortex/server.py` (Cortex Flask Server)

### 13.1. Purpose

(🟡 UNCONFIRMED - Inferred to be the main Flask application script that initializes and runs the Cortex microservice, exposing the `CortexAPI` endpoints as a web server.)

### 13.2. Key Components & Logic

- (🟡 UNCONFIRMED - Would likely involve creating a Flask app instance, initializing `CortexAPI`, and defining routes that map to `CortexAPI` methods.)

### 13.3. Dependencies

- `flask` (web framework).
- `services.cortex.api.CortexAPI` (to expose its functionalities).

### 13.4. Invariants & Assumptions

- **Web Server:** Acts as the HTTP server for the Cortex API.
- **API Exposure:** Assumed to correctly map Flask routes to `CortexAPI` methods.
- **Deployment Ready:** Should be configured for production deployment (e.g., using Gunicorn or similar WSGI server).