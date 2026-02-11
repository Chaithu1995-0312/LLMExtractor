# FILE INDEX

This document provides an index of all significant files within the `src/nexus` directory, detailing their classes and a brief, 1-2 line summary of each method.

## `src/nexus/config.py`
- **Description**: Defines various base paths, data directories, output paths, and system-wide constants.
- **Classes**: None
- **Functions**: None

## `src/nexus/utils_logging.py`
#### Class: `MultiWriter`
- `__init__`: Initializes a writer that dispatches output to multiple streams.
- `write`: Writes data to all registered streams.
- `flush`: Flushes all registered streams.
- `isatty`: Reports `False` to prevent terminal-specific formatting issues when redirecting.
#### Function: `setup_logging`
- `setup_logging`: Configures system logging to output to both console and a time-stamped log file.

## `src/nexus/ask/recall.py`
- **Description**: Provides functionality for recalling relevant bricks using vector search, hierarchical access control, and reranking.
#### Functions:
- `_normalize_faiss_output`: Converts FAISS raw output to a flat list.
- `get_reranker`: Lazily initializes and returns the `RerankOrchestrator`.
- `_normalize_distance_to_confidence`: Maps FAISS distance scores to a confidence range [0.0, 1.0].
- `get_scope_hierarchy`: Recursively fetches the parent scope hierarchy for a given scope.
- `recall_bricks`: Performs vector search, ACL filtering, and reranking of bricks.
- `recall_bricks_readonly`: A read-only alias for `recall_bricks`.
- `get_recall_brick_metadata`: Retrieves metadata for a specific brick.
- `get_related_intents`: Traverses the graph to find intents or artifacts related to bricks.

## `src/nexus/bricks/brick_store.py`
- **Description**: Manages the storage and retrieval of brick metadata and content from the database.
#### Class: `BrickStore`
- `__init__`: Initializes the brick store with a database connection.
- `_load_all_bricks_metadata`: Deprecated; the database is the source of truth.
- `get_brick_metadata`: Retrieves a brick's metadata from the database.
- `get_brick_text`: Retrieves a brick's raw text content from the database.

## `src/nexus/bricks/extractor.py`
- **Description**: Handles the extraction and classification of atomic bricks from raw conversational data.
#### Functions:
- `classify_brick_type`: Deterministically classifies the type of a brick (query, answer, input, doctrine, unknown).
- `generate_brick_id`: Generates a unique and stable SHA256 hash-based ID for each brick.
- `extract_bricks_from_file`: Processes a conversation tree file to extract individual content blocks as atomic bricks.
- `_create_brick`: A helper to construct a standardized brick object with metadata and provenance.

## `src/nexus/bricks/resolver.py`
- **Description**: Implements logic for a user-triggered resolution of loose bricks based on conversational patterns.
#### Class: `UserTriggeredResolver`
- `__init__`: Initializes the resolver with a reference to the `GraphManager`.
- `is_triggered`: Determines if the resolution mechanism should activate based on the user's input text.
- `split_user_blocks`: Divides user input into distinct blocks, handling list formats and numbering.
- `is_covered`: Checks for deterministic structural overlap between a question and an answer block.
- `resolve`: Processes a topic to match loose bricks with user input, marking covered bricks as `FORMING`.

## `src/nexus/cli/main.py`
- **Description**: Provides the command-line interface for the Nexus system.
#### Functions:
- `get_utc_now`: Returns the current UTC timestamp.
- `sanitize_filename`: Cleans a string for use as a safe filename.
- `cmd_extract`: CLI subcommand to extract conversation trees and bricks.
- `cmd_wall`: CLI subcommand to build token-aware walls from extracted data.
- `cmd_sync`: CLI subcommand to run the autonomous ingestion and synchronization process.
- `cmd_ask`: CLI subcommand to perform semantic recall and generate answers.
- `main`: Parses CLI arguments and dispatches to the appropriate subcommand.

## `src/nexus/cognition/assembler.py`
- **Description**: Orchestrates the assembly of canonical cognition artifacts for specific topics.
#### Functions:
- `_get_slug`: Generates a URL/filename-safe slug from text.
- `_calculate_content_hash`: Computes a SHA256 hash of JSON-serializable content.
- `_load_tree_file`: Loads a conversation tree file from the filesystem.
- `assemble_topic`: Coordinates recalling bricks, expanding sources, deduplicating, performing cognitive extraction via DSPy, persisting the artifact, and linking it to the knowledge graph with conflict resolution.

## `src/nexus/cognition/coverage_scorer.py`
- **Description**: Calculates a quantitative coverage score for topics based on governance alerts and intent stability.
#### Class: `CoverageScorer`
- `__init__`: Initializes with `GraphManager` and `AlertManager` dependencies.
- `compute_score`: Calculates a weighted coverage score for a given topic, factoring in gaps, redundancy, orphans, and frozen intents.

## `src/nexus/cognition/coverage_sentinel.py`
- **Description**: Uses an LLM to analyze topics for structural weaknesses and emit coverage alerts.
#### Class: `CoverageSentinel`
- `__init__`: Initializes with an LLM client and a deque for tracking recent alert fingerprints.
- `analyze_topic`: Analyzes bricks and intents for issues like redundancy, missing questions, or contradictions, generating alerts.
- `_generate_fingerprint`: Creates a stable, deterministic hash for an alert to detect duplicates.
- `_clean_llm_response`: Extracts JSON content from LLM responses that may be wrapped in markdown.

## `src/nexus/cognition/dspy_modules.py`
- **Description**: Defines DSPy signatures and modules for various LLM-driven cognitive tasks.
#### Class: `FactSignature`
- *(DSPy Signature)*: Defines the schema for extracting atomic propositional facts from text.
#### Class: `DiagramSignature`
- *(DSPy Signature)*: Defines the schema for extracting LaTeX formulas and Mermaid.js diagrams.
#### Class: `RelationshipSignature`
- *(DSPy Signature)*: Defines the schema for extracting relationships between intents.
#### Class: `EntitySignature`
- *(DSPy Signature)*: Defines the schema for identifying key entities and technical components.
#### Class: `CognitiveExtractor`
- `__init__`: Sets up the internal DSPy modules for fact, diagram, and entity extraction.
- `forward`: Executes the multi-stage extraction process, potentially recursively for entities.
#### Class: `SentimentSignature`
- *(DSPy Signature)*: Defines the schema for analyzing the urgency and sentiment of a query.
#### Class: `RelationshipSynthesizer`
- `__init__`: Sets up the internal DSPy modules for relationship synthesis and sentiment analysis.
- `analyze_sentiment`: Analyzes the sentiment and urgency of a given query (note: actual implementation in `_sentiment_analyzer` in the prompt, not a separate method).
- `forward`: Synthesizes relationships between a list of intents, considering existing graph topology.

## `src/nexus/cognition/prompt_generator.py`
- **Description**: Generates targeted ingestion prompts to address identified knowledge gaps.
#### Class: `PromptGenerator`
- `__init__`: Initializes with LLM client, alert manager, and coverage scorer.
- `generate_prompts`: Checks eligibility of alerts and uses an LLM to generate actionable prompts to fill knowledge gaps.
- `_clean_llm_response`: Extracts JSON content from LLM responses that may be wrapped in markdown.

## `src/nexus/cognition/synthesizer.py`
- **Description**: Facilitates the automatic discovery and registration of relationships within the knowledge graph.
#### Function: `run_relationship_synthesis`
- `run_relationship_synthesis`: Scans intents, batches them, uses `RelationshipSynthesizer` to discover relationships, and registers new edges in the graph.

## `src/nexus/extract/tree_splitter.py`
- **Description**: Processes raw conversational data to extract linear conversation paths and structured messages.
#### Functions:
- `get_utc_timestamp`: Converts a given timestamp to UTC ISO format.
- `find_root_nodes`: Identifies the starting points (root messages) in a conversation tree.
- `dfs_paths`: Performs a Depth-First Search to enumerate all possible linear conversation paths.
- `extract_message`: Transforms a raw message node into a structured message object, including content blocks and metadata.
- `process_conversation`: Takes a raw conversation object and generates multiple structured tree path files on disk.
- `load_conversations`: Loads raw conversation data from a JSON file, supporting different formats.

## `src/nexus/governance/alert_manager.py`
- **Description**: Manages the lifecycle and persistence of coverage alerts and prompt generation attempts.
#### Class: `AlertManager`
- `__init__`: Initializes the manager with the path to the SQLite database.
- `_get_conn`: Provides a connection object to the SQLite database.
- `persist_alert`: Inserts or ignores a coverage alert into the database, handling duplicates via fingerprint. *(Note: `details` are currently stored in `resolution_metadata` due to schema evolution.)*
- `get_alerts_for_topic`: Retrieves all coverage alerts associated with a specific topic.
- `acknowledge_alert`: Marks a given alert as acknowledged by an actor.
- `dismiss_alert`: Marks a given alert as dismissed with a reason.
- `resolve_alert`: Marks a given alert as resolved with an action and metadata.
- `archive_alert`: Archives an alert if it is in a resolved or dismissed state.
- `log_prompt_attempt`: Records details of an attempt to generate prompts for an alert.
- `get_recent_prompt_attempts`: Fetches the most recent prompt generation attempts for a topic.
- `get_alert`: Retrieves a single alert record by its ID.
- `_transition_state`: Internal method to update an alert's state and associated metadata, ensuring auditability.

## `src/nexus/graph/manager.py`
- **Description**: The central interface for interacting with and managing the SQLite-backed knowledge graph.
#### Class: `GraphTransaction`
- `__init__`: Prepares a database transaction with a connection.
- `__enter__`: Initiates a database transaction or a nested savepoint.
- `__exit__`: Handles transaction commit or rollback, including savepoint release.
#### Class: `GraphManager`
- `__init__`: Initializes the graph manager, ensuring the database schema is set up and performing initial brick synchronization.
- `_init_db`: Sets up the core `nodes` and `edges` tables and runs the `schema_sync.sql`.
- `_get_conn`: Provides a connection to the SQLite database.
- `register_node`: Adds a new node or updates an existing one if `merge` is true.
- `get_intents_by_topic`: Retrieves all intent nodes linked to a specific topic.
- `_check_for_cycle`: Detects cycles in the graph for specific edge types to enforce invariants.
- `register_edge`: Adds a new edge between nodes, including real-time cycle prevention for `OVERRIDES` and `SUPERSEDED_BY` types.
- `add_intent`: Creates and registers an `Intent` node.
- `add_source`: Creates and registers a `Source` node.
- `add_scope`: Creates and registers a `ScopeNode`.
- `_get_node_data`: Fetches the raw data (JSON string) of a node.
- `get_node`: Retrieves the type and parsed data of a node.
- `_emit_pulse`: Emits a standardized audit event to an L1 Narrator (currently prints to console).
- `_log_audit_event`: Appends a structured audit event to the `phase3_audit_trace.jsonl` file, enforcing cost invariants.
- `kill_node`: Marks a node with a `KILLED` lifecycle state, preserving its history.
- `promote_node_to_frozen`: Transitions a `FORMING` node to `FROZEN`, converting associated soft anchors to hard ones.
- `supersede_node`: Establishes an `OVERRIDES` relationship between two `FROZEN` nodes, marking the older as superseded.
- `promote_intent`: Manages the lifecycle state transitions of an intent, enforcing monotonicity and specific invariants.
- `add_typed_edge`: Registers a new edge, applying write-time invariants for specific edge types.
- `get_all_intents`: Retrieves all intent nodes in the graph.
- `get_all_edges`: Retrieves all edges in the graph as `Edge` objects.
- `get_edges_for_node`: Fetches all incoming and outgoing edges connected to a specific node.
- `get_all_scopes`: Retrieves all scope nodes in the graph.
- `get_all_sources`: Retrieves all source nodes in the graph.
- `delete_node`: Removes a node and all its connected edges from the graph.
- `get_loose_bricks`: Queries for bricks that are currently in a `LOOSE` state for a given topic.
- `mark_forming`: Updates a brick's state to `FORMING` with resolution metadata.
- `get_all_nodes_raw`: Fetches all nodes in the graph as raw dictionary objects.
- `sync_bricks_to_nodes`: Migrates historical bricks data from the `bricks` table to the unified `nodes` table.
- `get_all_edges_raw`: Fetches all edges in the graph as raw dictionary objects.
- `query_audit_logs`: Reads and filters audit events from the `phase3_audit_trace.jsonl` file.

## `src/nexus/graph/prompt_manager.py`
- **Description**: Governs access to and versioning of LLM prompts stored in the database.
#### Class: `GovernanceViolation`
- *(Exception Class)*: A specific exception signaling a breach in prompt governance rules.
#### Class: `PromptManager`
- `__init__`: Initializes the prompt manager, connecting to the database and setting up an in-memory cache.
- `_get_conn`: Provides a connection object to the SQLite database.
- `get_prompt`: Retrieves a specific version of a prompt or the latest, with critical governance checks and fallback mechanisms.
- `save_prompt`: Stores a new version of a prompt, automatically incrementing its version and invalidating relevant cache entries.
- `get_all_system_prompts`: Retrieves the latest version of all defined system prompts.

## `src/nexus/graph/projection.py`
- **Description**: Defines the logic for projecting and categorizing knowledge graph intents onto a conceptual 3x3 `WallCell` grid.
#### Enum: `WallCell`
- *(Enum Class)*: Defines the distinct categories (e.g., `FROZEN_RULES`, `CONFLICTS`, `HISTORICAL`) that intents can be projected into.
#### Functions:
- `get_intent_edges`: Retrieves both incoming and outgoing edges specifically connected to an intent node.
- `is_global_scope`: Determines if an intent is explicitly linked to the global scope.
- `has_conflict`: Implements complex logic to detect various types of conflicts (explicit, structural, source-level competition) impacting an intent.
- `is_from_agent`: Checks if an intent originated from an agent-generated source.
- `project_intent`: The core projection function that assigns an intent to a specific `WallCell` based on its lifecycle, conflicts, scope, and provenance.

## `src/nexus/graph/schema.py`
- **Description**: Defines the core data models, enums, and dataclasses that constitute the Nexus knowledge graph schema.
#### Enum: `IntentLifecycle`
- *(Enum Class)*: Represents the lifecycle states of an intent (e.g., `LOOSE`, `FORMING`, `FROZEN`, `KILLED`).
#### Enum: `IntentType`
- *(Enum Class)*: Categorizes the nature of an intent (e.g., `RULE`, `FACT`, `STRUCTURE`, `QUESTION`).
#### Enum: `EdgeType`
- *(Enum Class)*: Defines the types of relationships that can exist between nodes in the graph (e.g., `DERIVED_FROM`, `APPLIES_TO`, `OVERRIDES`, `CONFLICTS_WITH`, `REFINES`, `DEPENDS_ON`, `ASSEMBLED_IN`, `SUPERSEDED_BY`).
#### Enum: `AuditEventType`
- *(Enum Class)*: Lists standardized event types for auditing system operations and LLM interactions.
#### Enum: `ModelTier`
- *(Enum Class)*: Classifies LLM models into tiers based on cost and capability (`L1`, `L2`, `L3`).
#### Enum: `DecisionAction`
- *(Enum Class)*: Enumerates possible actions taken in system decisions (e.g., `LLM_CALL`, `ACCEPTED`, `REJECTED`, `PROMOTED`, `SUPERSEDED`, `BLOCKED`).
#### Class: `GraphNode`
- *(Dataclass)*: The base class for all nodes in the knowledge graph, providing common attributes like ID and creation timestamp.
#### Class: `Source`
- *(Dataclass)*: Represents a source artifact node in the graph, containing content and origin details.
#### Class: `ScopeNode`
- *(Dataclass)*: Represents a scope or context node, defining a boundary for intents.
#### Class: `Intent`
- *(Dataclass)*: Represents a knowledge intent node, including its statement, lifecycle, and type.
#### Class: `Edge`
- *(Dataclass)*: Represents a directed edge between two graph nodes, specifying its type and metadata.

## `src/nexus/graph/schema_sync.sql`
- **Description**: Defines the SQLite database schema for the Nexus synchronization and governance components.
- **Tables**: `topics`, `source_runs`, `bricks`, `prompts`, `coverage_alerts`, `coverage_prompt_attempts`.
- **Views**: `active_alerts`.
- **Indexes**: Various indexes for performance on topic, fingerprint, slug, and state columns.

## `src/nexus/index/conversation_index.py`
- **Description**: Manages an on-disk index of processed conversations for quick lookup and metadata retrieval.
#### Class: `ConversationIndex`
- `__init__`: Initializes the index, loading from `conversation_index.json` or creating an empty one.
- `load`: Reads the conversation index from its JSON persistence file.
- `save`: Writes the current state of the conversation index to disk.
- `add_conversation`: Registers or updates metadata for a conversation, including its ID, title, and source.
- `get_metadata`: Retrieves all stored metadata for a given conversation ID.
- `list_conversations`: Returns a list of all conversations currently in the index.
- `export_chat_mapping`: Generates and saves a simplified `chat_id: title` mapping, typically for UI consumption.

## `src/nexus/rerank/cross_encoder.py`
- **Description**: Implements a secondary reranking mechanism using a `sentence-transformers` CrossEncoder model.
#### Class: `CrossEncoderReranker`
- `__init__`: Loads the `cross-encoder/ms-marco-TinyBERT-L-2-v2` model and ensures deterministic behavior.
- `rank`: Reranks a list of candidate bricks against a query using the CrossEncoder, normalizing and sorting scores.

## `src/nexus/rerank/heuristic.py`
- **Description**: Provides a tertiary, dependency-free reranking mechanism based on lexical heuristics.
#### Class: `HeuristicReranker`
- `rank`: Reranks candidates by calculating token overlap and detecting exact phrase matches, combining with base confidence.

## `src/nexus/rerank/llm_reranker.py`
- **Description**: Implements the primary reranking mechanism utilizing a local quantized LLM.
#### Class: `LlmReranker`
- `__init__`: Initializes the local LLM (`llama-cpp-python`) for reranking, with checks for model availability and deterministic settings.
- `_get_cached_score`: Placeholder for potential future caching of LLM-generated scores for query-text pairs.
- `rank`: Reranks candidate bricks by querying the local LLM for relevance scores, including latency monitoring and fallback logic.

## `src/nexus/rerank/orchestrator.py`
- **Description**: Manages and orchestrates the multi-stage reranking pipeline with robust fallback mechanisms.
#### Class: `RerankOrchestrator`
- `__init__`: Initializes the primary (LLM), secondary (CrossEncoder), and tertiary (Heuristic) rerankers, gracefully handling initialization failures.
- `rerank`: Executes the reranking process, attempting the primary reranker first and falling back to subsequent stages if failures occur.

## `src/nexus/sync/__main__.py`
- **Description**: The command-line entry point for the `nexus sync` operation.
- **Functions**: None (directly calls `run_sync` after argument parsing).

## `src/nexus/sync/compiler.py`
- **Description**: Core of the ingestion pipeline, responsible for transforming raw data into structured bricks with zero-trust validation.
#### Class: `NexusCompiler`
- `_run_async`: A utility to safely execute asynchronous coroutines from synchronous code.
- `__init__`: Initializes the compiler with database, LLM client, prompt manager, coverage sentinel, and alert manager dependencies.
- `compile_run`: Orchestrates the full compilation process for a source run and topic, including filtering, batching, LLM extraction, mechanical validation, and coverage analysis.
- `_reject_message`: Applies initial, cheap structural checks to filter out irrelevant messages.
- `_has_signal`: Performs a lexical scan to identify messages containing high-signal keywords for processing.
- `_pre_filter_nodes`: Filters raw conversation messages based on incremental boundaries, message authority, and content signal.
- `_build_batches`: Groups filtered messages into token-bounded batches suitable for LLM processing.
- `_llm_extract_pointers`: Uses a structured LLM (`StructuredIngestLLM`) to extract specific data pointers (quotes and paths) from message batches.
- `_clean_llm_response`: Standardizes LLM output by removing markdown wrappers.
- `_materialize_brick`: The critical Zero-Trust Validation Gate, verifying LLM-extracted pointers against the raw source content to prevent hallucination.
- `_resolve_json_path`: Robustly resolves JSONPaths within the raw conversation data to pinpoint content.

## `src/nexus/sync/db.py`
- **Description**: Provides a direct interface for managing the SQLite database tables specific to the synchronization process.
#### Class: `SyncDatabase`
- `__init__`: Initializes the database connection and ensures the schema is up-to-date.
- `_init_db`: Executes the `SYNC_SCHEMA_PATH` SQL script to set up database tables.
- `_get_conn`: Returns an active SQLite database connection object.
- `create_topic`: Inserts a new topic record into the `topics` table.
- `get_topic`: Retrieves a specific topic by its ID.
- `get_all_topics`: Fetches all defined topics from the database.
- `register_run`: Records a new source run (e.g., a processed conversation tree file) in the `source_runs` table.
- `get_run`: Retrieves a specific source run by its ID.
- `update_run_boundary`: Updates the `last_processed_index` of a source run for incremental processing.
- `save_brick`: Stores a new brick and atomically updates its representation in the unified graph `nodes` table.
- `get_fingerprints_for_topic`: Retrieves all unique content fingerprints of bricks associated with a topic.
- `get_bricks_for_topic`: Fetches all bricks for a given topic, ordered by creation time.
- `truncate_sync_data`: Clears all synchronization-related data, including bricks and source runs, and resets the unified graph for a full rebuild.

## `src/nexus/sync/ingest_history.py`
- **Description**: Handles the ingestion of historical conversation data into the Nexus system, involving brickification and vector indexing.
#### Class: `NexusIngestor`
- `__init__`: Initializes the ingestor with Pinecone API key, dry run status, and an embedder, handling `PineconeVectorIndex` setup.
- `brickify`: Chunks raw text content into semantic atomic bricks for the vector index.
- `ingest_history`: Processes files in an input directory, performs vector ingestion (embedding and upserting to Pinecone), and triggers semantic assembly via `assemble_topic`.

## `src/nexus/sync/llm.py`
- **Description**: Manages LLM routing, client interactions, and structured ingestion for the Nexus system.
#### Enums: `LLMIntentClass`, `CostTolerance`, `LLMTier`, `LLMProvider`
- *(Enum Classes)*: Defines classifications for LLM intentions, cost constraints, model tiers, and providers.
#### Dataclasses: `LLMRequest`, `LLMRoute`
- *(Dataclasses)*: Structured objects representing an LLM request and its determined routing path.
#### Class: `LLMRoutingError`
- *(Exception Class)*: Custom exception raised when an LLM request cannot be routed successfully.
#### Class: `LLMRouter`
- `__init__`: Configures the router based on environment variables for local LLM enablement and API keys.
- `route`: Deterministically selects the appropriate LLM model and provider based on request intent and cost tolerance, following frozen routing rules.
#### Class: `LLMClient`
- `__init__`: Initializes the client with API key and a router, providing a unified interface for LLM calls.
- `generate`: The primary method for making LLM calls, abstracting routing, handling fallbacks, and supporting different providers.
- `_call_ollama`: Handles the specific HTTP request and response parsing for Ollama-based local LLM interactions.
- `_mock_response`: Provides mock LLM responses for testing and development, simulating successful extraction or empty results.
#### Pydantic Models: `PointerObject`, `ExtractionResponse`
- *(Pydantic Models)*: Defines the structured data types for LLM extraction outputs (pointers to verbatim quotes and their JSON paths).
#### Class: `StructuredIngestLLM`
- `__init__`: Configures a specialized LLM client for structured data extraction, often using `llama_index` capabilities.
- `extract`: Performs structured extraction of pointers from text, supporting mock mode and error recovery for large inputs.
- `_mock_extract`: Provides mock structured extraction responses, intelligently synthesizing pointers from the prompt for testing.

## `src/nexus/sync/runner.py`
- **Description**: Orchestrates the entire synchronization and ingestion pipeline, from raw conversations to compiled knowledge bricks.
#### Function: `run_sync`
- `run_sync`: The main control flow, setting up logging, initializing the database and compiler, loading conversations, processing them into runs, and compiling bricks against all active topics incrementally.

## `src/nexus/vector/embedder.py`
- **Description**: Manages the generation of vector embeddings for text, supporting query expansion.
#### Class: `VectorEmbedder`
- `__init__`: Initializes the embedder, specifying the `sentence-transformers` model to use.
- `_get_model`: Lazily loads and caches the `SentenceTransformer` model to ensure efficient resource usage.
- `_rewrite_with_llm`: Optionally uses an external LLM (e.g., GPT-4o) to enhance or expand complex search queries for better recall.
- `embed_query`: Converts a single query string into its corresponding vector embedding, with optional LLM rewriting.
- `embed_texts`: Processes a list of text documents, converting them into a matrix of vector embeddings while enforcing character limits and batching.
#### Function: `get_embedder`
- `get_embedder`: Provides a global access point to the `VectorEmbedder` instance (marked as deprecated in favor of direct instantiation).

## `src/nexus/vector/index.py`
- **Description**: A public API facade that re-exports the `LocalVectorIndex` as the primary `VectorIndex` implementation.
- **Classes**: None (re-exports `LocalVectorIndex`)
- **Functions**: None

## `src/nexus/vector/local_index.py`
- **Description**: Implements a local, disk-backed FAISS index for efficient similarity search of vector embeddings.
#### Class: `LocalVectorIndex`
- `__init__`: Initializes the FAISS index and the associated store of brick IDs, loading existing data if available.
- `load`: Reads the FAISS index and the list of brick IDs from specified files on disk.
- `save`: Persists the current state of the FAISS index and brick IDs to disk.
- `add_bricks`: Processes a list of bricks, embeds their content using the `VectorEmbedder`, and adds these embeddings to the FAISS index.
- `search`: Performs a similarity search, returning distances and indices of the nearest neighbors for a given query vector.

## `src/nexus/walls/builder.py`
- **Description**: Constructs token-aware Markdown walls from conversation tree files, aggregating content within target token limits.
#### Functions:
- `get_tokenizer`: Retrieves a `tiktoken` encoder for accurate token counting.
- `build_walls`: Organizes processed conversation trees into paginated Markdown files, each adhering to a maximum token count.
