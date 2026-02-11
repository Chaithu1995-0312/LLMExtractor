# IMPLEMENTATION REALITY MAP

This document maps the intended architectural components and functionalities to their current implementation status within the Nexus codebase. Statuses are categorized as follows:
- ✅ Implemented: Fully functional and stable.
- 🟡 Partial: Implemented but with known limitations, pending features, or ongoing refinement.
- 🔴 Missing: Declared or implied functionality that is not yet implemented.
- 🧪 Mocked: Functionality that is mocked for testing or development, not using a live external dependency.

## Nexus Core Components (src/nexus)

### `nexus.utils_logging`

#### Class: `MultiWriter`
- `__init__` ✅: Initializes the MultiWriter with multiple streams, inheriting encoding and error handling.
- `write` ✅: Writes data to all configured streams and flushes them.
- `flush` ✅: Flushes all configured streams.
- `isatty` ✅: Returns False to prevent terminal-specific formatting issues.

#### Function: `setup_logging`
- `setup_logging` ✅: Sets up logging to console and a unique file, wrapping `sys.stdout` and `sys.stderr` with `MultiWriter`.

### `nexus.ask.recall`

#### Function: `_normalize_faiss_output`
- `_normalize_faiss_output` ✅: Flattens and converts FAISS search output to a list.

#### Function: `get_reranker`
- `get_reranker` ✅: Lazily initializes and returns the `RerankOrchestrator`.

#### Function: `_normalize_distance_to_confidence`
- `_normalize_distance_to_confidence` ✅: Maps FAISS distance scores to a confidence range [0.0, 1.0].

#### Function: `get_scope_hierarchy`
- `get_scope_hierarchy` ✅: Recursively fetches the parent scope hierarchy for a given scope using `GraphManager`.

#### Function: `recall_bricks`
- `recall_bricks` ✅: Performs vector search, hierarchical ACL filtering, and reranking to retrieve relevant bricks.

#### Function: `recall_bricks_readonly`
- `recall_bricks_readonly` ✅: Alias for `recall_bricks` for explicit read-only operations.

#### Function: `get_recall_brick_metadata`
- `get_recall_brick_metadata` ✅: Retrieves metadata for a specific brick from the `BrickStore`.

#### Function: `get_related_intents`
- `get_related_intents` ✅: Traverses the graph to find intents or artifacts related to a list of brick IDs.

### `nexus.bricks.brick_store`

#### Class: `BrickStore`
- `__init__` ✅: Initializes the BrickStore with a `SyncDatabase` connection.
- `_load_all_bricks_metadata` 🔴: Marked as deprecated, indicating that the DB is the source of truth.
- `get_brick_metadata` ✅: Retrieves brick metadata from the database.
- `get_brick_text` ✅: Retrieves the raw text content of a brick from the database.

### `nexus.bricks.extractor`

#### Function: `classify_brick_type`
- `classify_brick_type` ✅: Classifies brick type based on role and text content (deterministic).

#### Function: `generate_brick_id`
- `generate_brick_id` ✅: Generates a unique, stable SHA256-based ID for a brick.

#### Function: `extract_bricks_from_file`
- `extract_bricks_from_file` ✅: Extracts atomic bricks from a conversation tree file using block-aware semantic distillation.

#### Function: `_create_brick`
- `_create_brick` ✅: Helper function to construct a standardized Brick object.

### `nexus.bricks.resolver`

#### Class: `UserTriggeredResolver`
- `__init__` ✅: Initializes the resolver with a `GraphManager` instance.
- `is_triggered` ✅: Detects if resolution logic should be triggered based on user text patterns.
- `split_user_blocks` ✅: Splits user text into potential answer blocks, handling numbering/list formatting.
- `is_covered` ✅: Performs a deterministic structural coverage check using substring overlap.
- `resolve` ✅: Runs the resolution algorithm on LOOSE bricks, marking them as FORMING if covered by user input.

### `nexus.cli.main`

#### Function: `get_utc_now`
- `get_utc_now` ✅: Returns the current UTC timestamp in ISO format.

#### Function: `sanitize_filename`
- `sanitize_filename` ✅: Sanitizes a string for use as a filename, enforcing length limits.

#### Function: `cmd_extract`
- `cmd_extract` ✅: CLI subcommand for extracting DFS trees and bricks from ChatGPT exports.

#### Function: `cmd_wall`
- `cmd_wall` ✅: CLI subcommand for building token-aware walls from extracted trees.

#### Function: `cmd_sync`
- `cmd_sync` ✅: CLI subcommand for running the autonomous ingestion and sync daemon.

#### Function: `cmd_ask`
- `cmd_ask` ✅: CLI subcommand for performing semantic recall and optionally generating answers using Cortex.

#### Function: `main`
- `main` ✅: Main entry point for the CLI, parses arguments and dispatches to subcommands.

### `nexus.cognition.assembler`

#### Function: `_get_slug`
- `_get_slug` ✅: Creates a filename-safe slug from text.

#### Function: `_calculate_content_hash`
- `_calculate_content_hash` ✅: Calculates SHA256 hash of JSON-serializable content.

#### Function: `_load_tree_file`
- `_load_tree_file` ✅: Loads a conversation tree file from disk.

#### Function: `assemble_topic`
- `assemble_topic` ✅: Orchestrates the assembly of a canonical cognition artifact for a given topic, including recall, expansion, deduplication, cognitive extraction via DSPy, persistence, and graph linkage with monotonic conflict resolution.

### `nexus.cognition.coverage_scorer`

#### Class: `CoverageScorer`
- `__init__` ✅: Initializes with `GraphManager` and `AlertManager` instances.
- `compute_score` ✅: Computes the coverage score for a topic based on active alerts and the ratio of frozen intents.

### `nexus.cognition.coverage_sentinel`

#### Class: `CoverageSentinel`
- `__init__` ✅: Initializes with an `LLMClient` and a history size for fingerprint deduplication.
- `analyze_topic` ✅: Analyzes a topic's content (bricks and intents) for structural weaknesses using an LLM, emitting coverage alerts.
- `_generate_fingerprint` ✅: Generates a deterministic fingerprint for an alert to detect duplicates.
- `_clean_llm_response` ✅: Helper to extract JSON from LLM markdown responses.

### `nexus.cognition.dspy_modules`

#### Class: `FactSignature`
- (DSPy Signature) ✅: Defines the input and output fields for extracting atomic facts.

#### Class: `DiagramSignature`
- (DSPy Signature) ✅: Defines the input and output fields for extracting LaTeX formulas and Mermaid.js diagrams.

#### Class: `RelationshipSignature`
- (DSPy Signature) ✅: Defines the input and output fields for analyzing intent relationships.

#### Class: `EntitySignature`
- (DSPy Signature) ✅: Defines the input and output fields for identifying key entities.

#### Class: `CognitiveExtractor`
- `__init__` ✅: Initializes DSPy chains for fact, diagram, and entity extraction.
- `forward` ✅: Executes the primary and potentially recursive extraction logic.

#### Class: `SentimentSignature`
- (DSPy Signature) ✅: Defines the input and output fields for analyzing query urgency and sentiment.

#### Class: `RelationshipSynthesizer`
- `__init__` ✅: Initializes DSPy chains for relationship synthesis and sentiment analysis.
- `analyze_sentiment` 🔴: Declared but not implemented beyond calling `sentiment_analyzer`. Likely a placeholder for future deeper integration.
- `forward` ✅: Executes relationship synthesis between intents, taking into account existing edges.

### `nexus.cognition.prompt_generator`

#### Class: `PromptGenerator`
- `__init__` ✅: Initializes with `LLMClient`, `AlertManager`, and `CoverageScorer` instances.
- `generate_prompts` ✅: Generates ingestion prompts for a given alert if eligibility checks pass, using an LLM.
- `_clean_llm_response` ✅: Helper to extract JSON from LLM markdown responses.

### `nexus.cognition.synthesizer`

#### Function: `run_relationship_synthesis`
- `run_relationship_synthesis` ✅: Orchestrates the automatic discovery and registration of relationships between intents using `GraphManager` and `RelationshipSynthesizer`.

### `nexus.extract.tree_splitter`

#### Function: `get_utc_timestamp`
- `get_utc_timestamp` ✅: Converts a timestamp to ISO format or returns current UTC.

#### Function: `find_root_nodes`
- `find_root_nodes` ✅: Identifies root nodes in a conversation mapping.

#### Function: `dfs_paths`
- `dfs_paths` ✅: Performs a Depth-First Search to find all conversation paths.

#### Function: `extract_message`
- `extract_message` ✅: Extracts and structures a single message, including rich content blocks and provenance.

#### Function: `process_conversation`
- `process_conversation` ✅: Takes a raw conversation, splits it into linear tree path files, and saves them to disk.

#### Function: `load_conversations`
- `load_conversations` ✅: Loads raw conversations from a JSON file, handling different formats.

### `nexus.governance.alert_manager`

#### Class: `AlertManager`
- `__init__` ✅: Initializes with the database path.
- `_get_conn` ✅: Returns a SQLite database connection.
- `persist_alert` 🟡: Persists a coverage alert. **Known Issue**: `details` JSON is stored in `resolution_metadata` due to schema mismatch. (See `GAPS_AND_TODOS.md`).
- `get_alerts_for_topic` ✅: Retrieves all alerts for a given topic.
- `acknowledge_alert` ✅: Transitions an alert to the ACKNOWLEDGED state.
- `dismiss_alert` ✅: Transitions an alert to the DISMISSED state.
- `resolve_alert` ✅: Transitions an alert to the RESOLVED state.
- `archive_alert` ✅: Transitions an alert to the ARCHIVED state after it has been resolved or dismissed.
- `log_prompt_attempt` ✅: Logs an attempt to generate prompts from an alert.
- `get_recent_prompt_attempts` ✅: Retrieves recent prompt attempts for a topic.
- `get_alert` ✅: Retrieves a single alert by ID.
- `_transition_state` ✅: Internal helper to manage alert state transitions with auditing.

### `nexus.graph.manager`

#### Class: `GraphTransaction`
- `__init__` ✅: Initializes a transaction with a database connection.
- `__enter__` ✅: Enters the transaction context, managing nested savepoints.
- `__exit__` ✅: Exits the transaction context, handling commit/rollback.

#### Class: `GraphManager`
- `__init__` ✅: Initializes the GraphManager, sets up the database, and syncs bricks to nodes.
- `_init_db` ✅: Initializes the SQLite database with `nodes` and `edges` tables, and executes `schema_sync.sql`.
- `_get_conn` ✅: Returns a SQLite database connection.
- `register_node` ✅: Registers a generic node, with optional merging for existing nodes.
- `get_intents_by_topic` ✅: Retrieves all intents linked to a specific topic.
- `_check_for_cycle` ✅: Detects cycles for a specific edge type (Guardrail 1: Type-scoped traversal).
- `register_edge` ✅: Registers an edge, with real-time cycle prevention for `OVERRIDES` and `SUPERSEDED_BY` edge types.
- `add_intent` ✅: Adds an `Intent` node to the graph.
- `add_source` ✅: Adds a `Source` node to the graph.
- `add_scope` ✅: Adds a `ScopeNode` to the graph.
- `_get_node_data` ✅: Retrieves raw JSON data for a node.
- `get_node` ✅: Retrieves node type and data.
- `_emit_pulse` ✅: Emits a standardized Pulse Envelope to the L1 Narrator (currently prints to console).
- `_log_audit_event` ✅: Logs a standardized audit event to `phase3_audit_trace.jsonl`, enforcing the Economic Cognition Invariant.
- `kill_node` ✅: Transitions a node to the KILLED lifecycle state, preserving history.
- `promote_node_to_frozen` ✅: Promotes a FORMING node to FROZEN, converting soft anchors to hard anchors.
- `supersede_node` ✅: Declares that one FROZEN node replaces another, creating a `SUPERSEDED_BY` edge.
- `promote_intent` ✅: Promotes an intent to a new lifecycle state, enforcing monotonicity and invariants.
- `add_typed_edge` ✅: Adds a typed edge, enforcing write-time invariants for `OVERRIDES` edges.
- `get_all_intents` ✅: Retrieves all intents in the graph.
- `get_all_edges` ✅: Retrieves all edges in the graph.
- `get_edges_for_node` ✅: Retrieves all incoming and outgoing edges for a node.
- `get_all_scopes` ✅: Retrieves all scope nodes.
- `get_all_sources` ✅: Retrieves all source nodes.
- `delete_node` ✅: Deletes a node and its connected edges.
- `get_loose_bricks` ✅: Fetches LOOSE query bricks for a topic from the unified nodes table.
- `mark_forming` ✅: Transitions a brick to the FORMING state with resolution metadata.
- `get_all_nodes_raw` ✅: Retrieves all nodes as raw dictionaries.
- `sync_bricks_to_nodes` ✅: Migrates bricks from the `bricks` sync table to the unified `nodes` table.
- `get_all_edges_raw` ✅: Retrieves all edges as raw dictionaries.
- `query_audit_logs` ✅: Queries the audit JSONL file.

### `nexus.graph.prompt_manager`

#### Class: `GovernanceViolation`
- (Exception Class) ✅: Custom exception for prompt governance violations.

#### Class: `PromptManager`
- `__init__` ✅: Initializes with database path and a cache.
- `_get_conn` ✅: Returns a SQLite database connection.
- `get_prompt` ✅: Retrieves a prompt by slug and version, with fallback and governance checks.
- `save_prompt` ✅: Saves a new version of a prompt, invalidating cache.
- `get_all_system_prompts` ✅: Retrieves the latest version of all system prompts.

### `nexus.graph.projection`

#### Enum: `WallCell`
- (Enum Class) ✅: Defines the categories for the 3x3 Wall grid.

#### Function: `get_intent_edges`
- `get_intent_edges` ✅: Helper to get incoming and outgoing edges for an intent.

#### Function: `is_global_scope`
- `is_global_scope` ✅: Checks if an intent applies to the GLOBAL scope.

#### Function: `has_conflict`
- `has_conflict` ✅: Detects active conflicts for an intent (explicit edges, structural, source-level competition).

#### Function: `is_from_agent`
- `is_from_agent` ✅: Checks if an intent is derived from an Agent source.

#### Function: `project_intent`
- `project_intent` ✅: Projects an `Intent` into a `WallCell` based on deterministic logic.

### `nexus.index.conversation_index`

#### Class: `ConversationIndex`
- `__init__` ✅: Initializes the index, loads it from disk, or creates an empty one.
- `load` ✅: Loads the conversation index from a JSON file.
- `save` ✅: Saves the conversation index to a JSON file.
- `add_conversation` ✅: Registers or updates conversation metadata in the index.
- `get_metadata` ✅: Retrieves metadata for a specific conversation.
- `list_conversations` ✅: Returns a list of all indexed conversations.
- `export_chat_mapping` ✅: Exports a simplified `chat_id: title` mapping for UI.

### `nexus.rerank.cross_encoder`

#### Class: `CrossEncoderReranker`
- `__init__` ✅: Initializes the CrossEncoder model (`ms-marco-TinyBERT-L-2-v2`).
- `rank` ✅: Ranks candidates using the CrossEncoder model, normalizing scores.

### `nexus.rerank.heuristic`

#### Class: `HeuristicReranker`
- `rank` ✅: Ranks candidates based on heuristic signals (token overlap, exact phrase match), preserving base confidence.

### `nexus.rerank.llm_reranker`

#### Class: `LlmReranker`
- `__init__` ✅: Initializes a local quantized LLM (e.g., Llama) for reranking, with timeout and model path checks.
- `_get_cached_score` 🔴: Declared as `@lru_cache` but method body is `return None`, indicating caching is intended but LLM scoring is not yet fully integrated with it, or it's a placeholder for future specific score caching.
- `rank` ✅: Ranks candidates using the LLM, with latency guards and fallback to base confidence.

### `nexus.rerank.orchestrator`

#### Class: `RerankOrchestrator`
- `__init__` ✅: Initializes the primary, secondary, and tertiary rerankers with graceful fallback on initialization failures.
- `rerank` ✅: Orchestrates the 3-stage reranking pipeline (LLM -> CrossEncoder -> Heuristic) with sequential fallback.

### `nexus.sync.compiler`

#### Class: `NexusCompiler`
- `_run_async` ✅: Helper to run async coroutines safely within sync or async contexts.
- `__init__` ✅: Initializes the compiler with `SyncDatabase`, `LLMClient`, `PromptManager`, `CoverageSentinel`, and `AlertManager`.
- `compile_run` ✅: Main entry point for the compiler, transforming raw run data into bricks for a topic, and triggering coverage analysis.
- `_reject_message` ✅: Implements cheap structural rejection logic for messages.
- `_has_signal` ✅: Implements lexical signal gate for message content.
- `_pre_filter_nodes` ✅: Filters raw content based on incremental boundaries, ingestion authority, structural rejection, and signal gate.
- `_build_batches` ✅: Constructs bounded batches of messages for LLM processing.
- `_llm_extract_pointers` ✅: Performs grammar-constrained pointer extraction using `StructuredIngestLLM`.
- `_clean_llm_response` ✅: Helper to extract JSON from LLM markdown responses.
- `_materialize_brick` ✅: The Zero-Trust Validation Gate, verifying LLM-extracted pointers against source data.
- `_resolve_json_path` ✅: Robust JSONPath resolver.

### `nexus.sync.db`

#### Class: `SyncDatabase`
- `__init__` ✅: Initializes the database connection and schema.
- `_init_db` ✅: Initializes the database with the schema from `SYNC_SCHEMA_PATH`.
- `_get_conn` ✅: Returns a SQLite database connection.
- `create_topic` ✅: Creates a new topic in the `topics` table.
- `get_topic` ✅: Retrieves a topic by ID.
- `get_all_topics` ✅: Retrieves all topics.
- `register_run` ✅: Registers a new source run.
- `get_run` ✅: Retrieves a source run by ID.
- `update_run_boundary` ✅: Updates the `last_processed_index` for a run.
- `save_brick` ✅: Saves a brick and atomically updates the unified `nodes` table.
- `get_fingerprints_for_topic` ✅: Retrieves all brick fingerprints for a topic.
- `get_bricks_for_topic` ✅: Retrieves all bricks for a topic.
- `truncate_sync_data` ✅: Clears all sync-related data, including `bricks`, `source_runs`, `nodes`, and `edges` for a full rebuild.

### `nexus.sync.ingest_history`

#### Class: `NexusIngestor`
- `__init__` ✅: Initializes with Pinecone API key and dry run flag. Handles `PineconeVectorIndex` loading or fallback to dry run.
- `brickify` ✅: Chunks text content into atomic bricks using paragraph-based splitting.
- `ingest_history` ✅: Processes files in an input directory, performs vector ingestion (embedding and upserting to Pinecone), and triggers semantic assembly via `assemble_topic`.

### `nexus.sync.llm`

#### Enum: `LLMIntentClass`, `CostTolerance`, `LLMTier`, `LLMProvider`
- (Enum Classes) ✅: Defines various LLM-related classification and routing parameters.

#### Class: `LLMRequest`, `LLMRoute`
- (Dataclasses) ✅: Represents LLM requests and routing decisions.

#### Class: `LLMRoutingError`
- (Exception Class) ✅: Custom exception for LLM routing failures.

#### Class: `LLMRouter`
- `__init__` ✅: Initializes router with local LLM and API key configurations.
- `route` ✅: Determines the execution path for an LLM request based on intent, cost tolerance, and availability.

#### Class: `LLMClient`
- `__init__` ✅: Initializes with API key, provider, and an `LLMRouter`.
- `generate` ✅: Generates a response from the LLM, handling routing and provider-specific calls (Ollama, mock, API placeholder).
- `_call_ollama` ✅: Handles HTTP calls to a local Ollama instance.
- `_mock_response` 🧪: Provides mock JSON responses, with some heuristic intelligence for testing. Marked as mocked due to its primary purpose for testing and fallback.

#### Class: `PointerObject`, `ExtractionResponse`
- (Pydantic Models) ✅: Defines the structured input/output for `StructuredIngestLLM`.

#### Class: `StructuredIngestLLM`
- `__init__` ✅: Initializes with a structured LLM client (`Ollama.as_structured_llm`).
- `extract` ✅: Performs structured extraction, supporting mock mode and error recovery.
- `_mock_extract` 🧪: Provides mock JSON responses for structured extraction, with some heuristic intelligence.

### `nexus.sync.runner`

#### Function: `run_sync`
- `run_sync` ✅: Orchestrates the entire synchronization process, from loading conversations to compiling and persisting bricks, and triggering coverage analysis.

### `nexus.vector.embedder`

#### Class: `VectorEmbedder`
- `__init__` ✅: Initializes with a model name.
- `_get_model` ✅: Loads and caches the `SentenceTransformer` model.
- `_rewrite_with_llm` 🟡: Optionally uses an LLM (GPT-4o) to expand/refine queries. This is functional but experimental and relies on external API, hence Partial.
- `embed_query` ✅: Embeds a single query string, optionally using LLM rewrite.
- `embed_texts` ✅: Embeds a list of texts, enforcing length limits and batch processing.

#### Function: `get_embedder`
- `get_embedder` 🟡: Global singleton accessor, but marked as deprecated in comments, suggesting a move to direct instantiation.

### `nexus.vector.local_index`

#### Class: `LocalVectorIndex`
- `__init__` ✅: Initializes a FAISS index and brick ID store, loading from disk if available.
- `load` ✅: Loads the FAISS index and brick IDs from disk.
- `save` ✅: Saves the FAISS index and brick IDs to disk.
- `add_bricks` ✅: Adds new bricks by embedding their content and updating the FAISS index and brick ID list.
- `search` ✅: Performs a similarity search against the FAISS index.

### `nexus.walls.builder`

#### Function: `get_tokenizer`
- `get_tokenizer` ✅: Retrieves a `tiktoken` tokenizer.

#### Function: `build_walls`
- `build_walls` ✅: Builds token-aware Markdown walls from conversation tree files, with YAML frontmatter.
