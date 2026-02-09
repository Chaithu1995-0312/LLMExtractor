# Nexus: Gaps and TODOs

## Knowledge & System Gaps 🔴
- **Missing Self-Healing**: The `trigger_self_healing` method in `CortexAPI` is a placeholder. It needs logic to resolve conflicts identified by `RelationshipSynthesizer`.
- **Incomplete Ingest History**: `NexusIngestor.ingest_history` lacks support for non-JSON formats (e.g., Markdown, PDF).
- **Static Coverage Sentinel**: `CoverageSentinel.analyze_topic` generates alerts but doesn't yet trigger automated `PromptGenerator` runs.
- **Weak Reranking**: Current reranker implementations are simplistic; missing cross-encoder integration in the primary `recall` path.

## Technical Debt 🟡
- **Vector Index Staleness**: Local vector index requires manual rebuilds via script; needs an event-driven update trigger in `GraphManager`.
- **Logging Verbosity**: `utils_logging` is inconsistent across modules; some use `logging` while others use custom print wrappers.
- **Test Coverage**: UI component tests (Jarvis) are missing for the `AuditPanel` and `WallView`.
- **Auth/Security**: `services/cortex/server.py` lacks API key validation or JWT integration.

## Immediate TODOs (Agent-Executable)
1. [ ] Implement `CortexAPI.trigger_self_healing` using a "Conflicting Intent Resolver" DSPy module.
2. [ ] Add `AUTO_REBUILD_VECTOR` flag to `GraphManager` to trigger `LocalVectorIndex.add_bricks` on node promotion.
3. [ ] Formalize `AlertManager.archive_alert` state transition logic to prevent database bloat.
4. [ ] Standardize the `audit_trace` output format between `CortexAPI` and `SyncCompiler`.
5. [ ] (IMPLIED) Create a `Prune` method in `GraphManager` to handle `KILLED` nodes and their associated edges.

## Future Research 🧪
- **Recursive Decomposition**: Investigating multi-hop graph traversals for complex "how-to" intent generation.
- **Agentic Refactoring**: Developing a "Graph-to-Code" pipeline that generates API stubs based on `FROZEN` intent definitions.
- **Cross-Topic Synthesis**: discovering relationships between disjoint topics via a global "Topic Hub" node.
