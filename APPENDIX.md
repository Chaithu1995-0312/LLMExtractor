# APPENDIX.md

## 1. Consolidated Class -> Method -> Responsibility -> Risk -> Used By Reference Table

This table provides a comprehensive reference of all classes and their methods, including their responsibilities, risk profiles, and a summary of where they are called from.

| Class | Method Name | Responsibility | Risk Profile | Used By | Layer | Type |
|---|---|---|---|---|---|---|
| `CortexAPI` | `__init__` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `CortexAPI` | `_audit_trace` | 🔴 MISSING_FROM_CONTEXT | MED: Local State/Disk | CortexAPI.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `CortexAPI` | `_fetch_graph_context` | 🔴 MISSING_FROM_CONTEXT | MED: Local State/Disk | CortexAPI.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `CortexAPI` | `_init_agent_embeddings` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | CortexAPI.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `CortexAPI` | `_reload_source_text` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | CortexAPI.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `CortexAPI` | `acknowledge_alert` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `CortexAPI` | `archive_alert` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `CortexAPI` | `ask_preview` | 🔴 MISSING_FROM_CONTEXT | MED: Local State/Disk | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `CortexAPI` | `assemble` | Endpoint: /cognition/assemble - Trigger topic assembly | MED: Local State/Disk | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `CortexAPI` | `calculate_complexity_score` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | CortexAPI.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `CortexAPI` | `dismiss_alert` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `CortexAPI` | `generate` | Endpoint: /generate - Now uses Tier 2 (The Voice) | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `CortexAPI` | `get_alerts` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `CortexAPI` | `get_all_prompts` | 🔴 MISSING_FROM_CONTEXT | MED: Local State/Disk | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `CortexAPI` | `get_audit_events` | 🔴 MISSING_FROM_CONTEXT | MED: Local State/Disk | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `CortexAPI` | `get_coverage_score` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `CortexAPI` | `get_graph_snapshot` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `CortexAPI` | `get_run_details` | 🔴 MISSING_FROM_CONTEXT | MED: Local State/Disk | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `CortexAPI` | `resolve_alert` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `CortexAPI` | `route` | Endpoint: /route - Urgency-aware Intent routing | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `CortexAPI` | `stream_audit_websocket` | Placeholder for real-time audit streaming. | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `CortexAPI` | `suggest_prompts` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `CortexAPI` | `synthesize` | Endpoint: /cognition/synthesize - Trigger relationship discovery | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `CortexAPI` | `trigger_self_healing` | Monitors vector index drift and triggers rebuild if necessary. | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `JarvisGateway` | `__init__` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `JarvisGateway` | `_call_proxy` | Helper to hit the budget-gated proxy. | LOW: Pure/Safe | JarvisGateway.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `JarvisGateway` | `explain` | TIER L2: The Voice (Cost: ~$0.01/call) | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `JarvisGateway` | `pulse` | TIER L1: The Pulse (Cost: $0.00) | MED: Local State/Disk | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `JarvisGateway` | `synthesize` | TIER L3: The Sage (Cost: ~$0.15/call) | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `BrickStore` | `__init__` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `BrickStore` | `_load_all_bricks_metadata` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `BrickStore` | `get_brick_metadata` | Retrieves brick metadata from the DB. | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `BrickStore` | `get_brick_text` | Retrieves the raw text content of a brick from the DB. | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `UserTriggeredResolver` | `__init__` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `UserTriggeredResolver` | `is_covered` | Deterministic structural coverage check using substring overlap. | LOW: Pure/Safe | UserTriggeredResolver.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `UserTriggeredResolver` | `is_triggered` | Detect if the resolution logic should be triggered. | LOW: Pure/Safe | UserTriggeredResolver.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `UserTriggeredResolver` | `resolve` | Run the resolution algorithm on LOOSE bricks. | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `UserTriggeredResolver` | `split_user_blocks` | Split user text into potential answer blocks. | LOW: Pure/Safe | UserTriggeredResolver.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `CoverageScorer` | `__init__` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `CoverageScorer` | `compute_score` | Computes the coverage score for a topic. | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `CoverageSentinel` | `__init__` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `CoverageSentinel` | `_clean_llm_response` | Helper to extract JSON from LLM markdown. | LOW: Pure/Safe | CoverageSentinel.[{', '.join(caller_methods)}]; PromptGenerator.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `CoverageSentinel` | `_generate_fingerprint` | Generates a deterministic fingerprint for an alert. | LOW: Pure/Safe | CoverageSentinel.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `CoverageSentinel` | `analyze_topic` | Analyzes a topic's content (bricks and intents) for structural weaknesses. | MED: Local State/Disk | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `CognitiveExtractor` | `__init__` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `CognitiveExtractor` | `forward` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `RelationshipSynthesizer` | `__init__` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `RelationshipSynthesizer` | `analyze_sentiment` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | CortexAPI.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `RelationshipSynthesizer` | `forward` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `PromptGenerator` | `__init__` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `PromptGenerator` | `_clean_llm_response` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | CoverageSentinel.[{', '.join(caller_methods)}]; PromptGenerator.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `PromptGenerator` | `generate_prompts` | Generates ingestion prompts for a given alert if eligibility checks pass. | MED: Local State/Disk | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `AlertManager` | `__init__` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `AlertManager` | `_get_conn` | 🔴 MISSING_FROM_CONTEXT | HIGH: DB Write/External API | AlertManager.[{', '.join(caller_methods)}]; GraphManager.[{', '.join(caller_methods)}]; PromptManager.[{', '.join(caller_methods)}]; SyncDatabase.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `AlertManager` | `_transition_state` | 🔴 MISSING_FROM_CONTEXT | HIGH: DB Write/External API | AlertManager.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `AlertManager` | `acknowledge_alert` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `AlertManager` | `archive_alert` | 🔴 MISSING_FROM_CONTEXT | HIGH: DB Write/External API | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `AlertManager` | `dismiss_alert` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `AlertManager` | `get_alert` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `AlertManager` | `get_alerts_for_topic` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `AlertManager` | `get_recent_prompt_attempts` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `AlertManager` | `log_prompt_attempt` | Log an auto-suggested prompt attempt. | HIGH: DB Write/External API | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `AlertManager` | `persist_alert` | Idempotent insert of a coverage alert. | HIGH: DB Write/External API | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `AlertManager` | `resolve_alert` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `GraphManager` | `__init__` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `GraphManager` | `_check_for_cycle` | DFS to detect cycles for a specific edge type. | LOW: Pure/Safe | GraphManager.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `GraphManager` | `_emit_pulse` | Fire-and-forget call to the L1 Narrator. | MED: Local State/Disk | GraphManager.[{', '.join(caller_methods)}]; NexusCompiler.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `GraphManager` | `_get_conn` | 🔴 MISSING_FROM_CONTEXT | HIGH: DB Write/External API | AlertManager.[{', '.join(caller_methods)}]; GraphManager.[{', '.join(caller_methods)}]; PromptManager.[{', '.join(caller_methods)}]; SyncDatabase.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `GraphManager` | `_get_node_data` | 🔴 MISSING_FROM_CONTEXT | MED: Local State/Disk | GraphManager.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `GraphManager` | `_init_db` | 🔴 MISSING_FROM_CONTEXT | HIGH: DB Write/External API | GraphManager.[{', '.join(caller_methods)}]; SyncDatabase.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `GraphManager` | `_log_audit_event` | Log a standardized audit event. Appends to phase3_audit_trace.jsonl. | MED: Local State/Disk | GraphManager.[{', '.join(caller_methods)}]; PromptManager.[{', '.join(caller_methods)}]; NexusCompiler.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `GraphManager` | `add_intent` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `GraphManager` | `add_scope` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `GraphManager` | `add_source` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `GraphManager` | `add_typed_edge` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `GraphManager` | `delete_node` | Delete a node and all connected edges. | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `GraphManager` | `get_all_edges` | 🔴 MISSING_FROM_CONTEXT | MED: Local State/Disk | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `GraphManager` | `get_all_edges_raw` | Retrieve all edges as dictionaries suitable for API response. | MED: Local State/Disk | CortexAPI.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `GraphManager` | `get_all_intents` | 🔴 MISSING_FROM_CONTEXT | MED: Local State/Disk | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `GraphManager` | `get_all_nodes_raw` | Retrieve all nodes as dictionaries suitable for API response. | MED: Local State/Disk | CortexAPI.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `GraphManager` | `get_all_scopes` | 🔴 MISSING_FROM_CONTEXT | MED: Local State/Disk | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `GraphManager` | `get_all_sources` | 🔴 MISSING_FROM_CONTEXT | MED: Local State/Disk | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `GraphManager` | `get_edges_for_node` | 🔴 MISSING_FROM_CONTEXT | MED: Local State/Disk | GraphManager.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `GraphManager` | `get_intents_by_topic` | Retrieve all intents linked to a specific topic. | MED: Local State/Disk | NexusCompiler.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `GraphManager` | `get_loose_bricks` | Governance helper: Fetch LOOSE query bricks for a specific topic. | MED: Local State/Disk | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `GraphManager` | `get_node` | Retrieve node type and data. | MED: Local State/Disk | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `GraphManager` | `kill_node` | Explicitly reject a node, moving it to KILLED lifecycle. | MED: Local State/Disk | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `GraphManager` | `mark_forming` | Transition a brick to FORMING state with resolution metadata. | HIGH: DB Write/External API | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `GraphManager` | `promote_intent` | Promote an intent to a new lifecycle state, enforcing monotonicity and invariants. | MED: Local State/Disk | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `GraphManager` | `promote_node_to_frozen` | Promote a FORMING node to FROZEN. | MED: Local State/Disk | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `GraphManager` | `query_audit_logs` | Governance Analytics: Query the audit JSONL file. | MED: Local State/Disk | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `GraphManager` | `register_edge` | Register an edge. Idempotent. | MED: Local State/Disk | GraphManager.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `GraphManager` | `register_node` | Register a generic node. Idempotent by default. | MED: Local State/Disk | GraphManager.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `GraphManager` | `supersede_node` | Declare that one node replaces another. | MED: Local State/Disk | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `GraphManager` | `sync_bricks_to_nodes` | Migrate bricks from the 'bricks' sync table into the unified 'nodes' table. | MED: Local State/Disk | GraphManager.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `GraphTransaction` | `__enter__` | 🔴 MISSING_FROM_CONTEXT | HIGH: DB Write/External API | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `GraphTransaction` | `__exit__` | 🔴 MISSING_FROM_CONTEXT | HIGH: DB Write/External API | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `GraphTransaction` | `__init__` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `PromptManager` | `__init__` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `PromptManager` | `_get_conn` | 🔴 MISSING_FROM_CONTEXT | HIGH: DB Write/External API | AlertManager.[{', '.join(caller_methods)}]; GraphManager.[{', '.join(caller_methods)}]; PromptManager.[{', '.join(caller_methods)}]; SyncDatabase.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `PromptManager` | `get_all_system_prompts` | Retrieves latest version of all system prompts. | LOW: Pure/Safe | CortexAPI.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `PromptManager` | `get_prompt` | Retrieves a prompt by slug. | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `PromptManager` | `save_prompt` | Saves a new prompt version. | HIGH: DB Write/External API | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `ConversationIndex` | `__init__` | 🔴 MISSING_FROM_CONTEXT | MED: Local State/Disk | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `ConversationIndex` | `add_conversation` | Register or update a conversation in the index. | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `ConversationIndex` | `export_chat_mapping` | Export the index as a simple {chat_id: title} mapping for the UI. | MED: Local State/Disk | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `ConversationIndex` | `get_metadata` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `ConversationIndex` | `list_conversations` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `ConversationIndex` | `load` | 🔴 MISSING_FROM_CONTEXT | MED: Local State/Disk | ConversationIndex.[{', '.join(caller_methods)}]; LocalVectorIndex.[{', '.join(caller_methods)}]; CortexAPI.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `ConversationIndex` | `save` | 🔴 MISSING_FROM_CONTEXT | MED: Local State/Disk | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `CrossEncoderReranker` | `__init__` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `CrossEncoderReranker` | `rank` | Ranks candidates using CrossEncoder. | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `HeuristicReranker` | `rank` | Ranks candidates based on heuristic signals. | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `LlmReranker` | `__init__` | 🔴 MISSING_FROM_CONTEXT | MED: Local State/Disk | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `LlmReranker` | `_get_cached_score` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `LlmReranker` | `rank` | Ranks using LLM scoring with latency guard. | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `RerankOrchestrator` | `__init__` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `RerankOrchestrator` | `rerank` | Executes reranking with fallback logic. | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `NexusCompiler` | `__init__` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `NexusCompiler` | `_build_batches` | Bounded batch construction algorithm. | MED: Local State/Disk | NexusCompiler.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `NexusCompiler` | `_clean_llm_response` | Helper to extract JSON from LLM markdown. | LOW: Pure/Safe | CoverageSentinel.[{', '.join(caller_methods)}]; PromptGenerator.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `NexusCompiler` | `_has_signal` | Lexical signal gate. | LOW: Pure/Safe | NexusCompiler.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `NexusCompiler` | `_llm_extract_pointers` | Grammar-constrained pointer extraction using a structured LLM. | MED: Local State/Disk | NexusCompiler.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `NexusCompiler` | `_materialize_brick` | The Zero-Trust Validation Gate. | LOW: Pure/Safe | NexusCompiler.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `NexusCompiler` | `_pre_filter_nodes` | Filters the raw content to reduce context window usage. | LOW: Pure/Safe | NexusCompiler.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `NexusCompiler` | `_reject_message` | Cheap structural rejection logic. | LOW: Pure/Safe | NexusCompiler.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `NexusCompiler` | `_resolve_json_path` | Robust JSONPath resolver with support for content_blocks using jsonpath-ng. | LOW: Pure/Safe | NexusCompiler.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `NexusCompiler` | `_run_async` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | NexusCompiler.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `NexusCompiler` | `compile_run` | Main entry point for the compiler. | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `SyncDatabase` | `__init__` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `SyncDatabase` | `_get_conn` | 🔴 MISSING_FROM_CONTEXT | HIGH: DB Write/External API | AlertManager.[{', '.join(caller_methods)}]; GraphManager.[{', '.join(caller_methods)}]; PromptManager.[{', '.join(caller_methods)}]; SyncDatabase.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `SyncDatabase` | `_init_db` | Initialize the database with the schema. | HIGH: DB Write/External API | GraphManager.[{', '.join(caller_methods)}]; SyncDatabase.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `SyncDatabase` | `create_topic` | 🔴 MISSING_FROM_CONTEXT | HIGH: DB Write/External API | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `SyncDatabase` | `get_all_topics` | 🔴 MISSING_FROM_CONTEXT | MED: Local State/Disk | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `SyncDatabase` | `get_bricks_for_topic` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `SyncDatabase` | `get_fingerprints_for_topic` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `SyncDatabase` | `get_run` | 🔴 MISSING_FROM_CONTEXT | MED: Local State/Disk | CortexAPI.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `SyncDatabase` | `get_topic` | 🔴 MISSING_FROM_CONTEXT | MED: Local State/Disk | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `SyncDatabase` | `register_run` | 🔴 MISSING_FROM_CONTEXT | HIGH: DB Write/External API | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `SyncDatabase` | `save_brick` | 🔴 MISSING_FROM_CONTEXT | HIGH: DB Write/External API | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `SyncDatabase` | `truncate_sync_data` | Clears all bricks and resets source runs for a full rebuild. | HIGH: DB Write/External API | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `SyncDatabase` | `update_run_boundary` | 🔴 MISSING_FROM_CONTEXT | HIGH: DB Write/External API | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `NexusIngestor` | `__init__` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `NexusIngestor` | `brickify` | Chunks text into atomic bricks for the vector index. | LOW: Pure/Safe | NexusIngestor.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `NexusIngestor` | `ingest_history` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `LLMClient` | `__init__` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `LLMClient` | `_call_ollama` | Calls local Ollama instance via HTTP. | MED: Local State/Disk | LLMClient.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `LLMClient` | `_mock_response` | Returns a valid JSON response for testing purposes. | MED: Local State/Disk | LLMClient.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `LLMClient` | `generate` | Generates a response from the LLM based on intent and routing. | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `LLMRouter` | `__init__` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `LLMRouter` | `route` | Determines the execution path for an LLM request based on the Canonical Routing Table. | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `StructuredIngestLLM` | `__init__` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `StructuredIngestLLM` | `_mock_extract` | Returns a valid JSON response for testing purposes. | MED: Local State/Disk | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `MultiWriter` | `__init__` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `MultiWriter` | `flush` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | MultiWriter.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `MultiWriter` | `isatty` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `MultiWriter` | `write` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | MultiWriter.[{', '.join(caller_methods)}]; GraphManager.[{', '.join(caller_methods)}]; CortexAPI.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `VectorEmbedder` | `__init__` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `VectorEmbedder` | `_get_model` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | VectorEmbedder.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `VectorEmbedder` | `_rewrite_with_llm` | Optional GENAI call to expand or refine the query. | LOW: Pure/Safe | VectorEmbedder.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `VectorEmbedder` | `embed_query` | Embeds a single query string into a 1x384 vector. | LOW: Pure/Safe | CortexAPI.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `VectorEmbedder` | `embed_texts` | Embeds a list of texts into a Nx384 matrix. | LOW: Pure/Safe | LocalVectorIndex.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `LocalVectorIndex` | `__init__` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `LocalVectorIndex` | `add_bricks` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `LocalVectorIndex` | `load` | 🔴 MISSING_FROM_CONTEXT | MED: Local State/Disk | ConversationIndex.[{', '.join(caller_methods)}]; LocalVectorIndex.[{', '.join(caller_methods)}]; CortexAPI.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `LocalVectorIndex` | `save` | 🔴 MISSING_FROM_CONTEXT | MED: Local State/Disk | None | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
| `LocalVectorIndex` | `search` | 🔴 MISSING_FROM_CONTEXT | LOW: Pure/Safe | LlmReranker.[{', '.join(caller_methods)}] | 🔴 MISSING_FROM_CONTEXT | 🔴 MISSING_FROM_CONTEXT |
