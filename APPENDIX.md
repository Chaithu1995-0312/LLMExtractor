# Appendix: Class & Method Reference Table

| Class | Method | Layer | Responsibility | Risk | Used By |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `SyncDatabase` | `register_run` | Ingestion | Store raw source content | MED | `runner.py` |
| `SyncDatabase` | `truncate_sync_data` | Ingestion | Wipe all sync state | HIGH | `runner.py` |
| `NexusCompiler` | `compile_run` | Ingestion | LLM extraction of bricks | MED | `runner.py` |
| `TreeSplitter` | `process_conversation` | Ingestion | Transform JSON tree to linear paths | MED | `runner.py` |
| `runner.py` | `run_sync` | Ingestion | Pipeline Orchestration | HIGH | CLI |
| `CognitiveExtractor` | `forward` | Cognition | Extract Facts/Entities | LOW | `NexusCompiler` |
| `RelationshipSynthesizer` | `forward` | Cognition | Infer Edges | LOW | `synthesizer.py` |
| `GraphManager` | `add_typed_edge` | Graph | Write Edge to DB | HIGH | `synthesizer.py` |
| `GraphManager` | `register_node` | Graph | Create/Update Node | HIGH | `server.py`, `runner.py` |
| `GraphManager` | `get_all_nodes_raw` | Graph | Read-only Node Dump | LOW | `server.py` |
| `GraphManager` | `sync_bricks_to_nodes` | Graph | Promote Bricks to Nodes | HIGH | `runner.py`, `server.py` |
| `PromptManager` | `get_prompt` | Governance | Retrieve approved prompts | MED | `compiler.py`, `synthesizer.py` |
| `PromptManager` | `save_prompt` | Governance | Version new prompt | HIGH | Governance CLI (implied) |
| `AlertManager` | `persist_alert` | Governance | Log coverage gaps | HIGH | `coverage_sentinel.py` |
| `CortexAPI` | `synthesize` | Service | Trigger Synthesis | MED | `server.py` |
| `Flask App` | `jarvis_anchor` | UI/API | User Validation Hook | HIGH | Jarvis UI |
| `LlmReranker` | `rank` | Service | Re-score recall candidates | MED | `recall.py` |
