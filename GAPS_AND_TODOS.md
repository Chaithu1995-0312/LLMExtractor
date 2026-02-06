# GAPS_AND_TODOS

## 1. Explicit Code TODOs
Items identified directly from file comments.

| File | Item | Status |
| :--- | :--- | :--- |
| `services/cortex/api.py` | Implementation of `verifier_node` for result validation | 🔴 |
| `services/cortex/api.py` | Implementation of `self_correction_node` for iterative refinement | 🔴 |
| `src/nexus/cognition/assembler.py` | Robust conflict resolution in `assemble_topic` | 🟡 |
| `src/nexus/sync/runner.py` | Async worker queue for long-running sync tasks | 🔴 |

## 2. Implied Method Gaps
Behavior described in architecture or requested by constraints, but missing from implementation.

| Class | Implied Method | Expected Responsibility | Status |
| :--- | :--- | :--- | :--- |
| `GraphManager` | `detect_conflicts` | Scan edges for contradictory claims between nodes. | 🧪 |
| `CortexAPI` | `enforce_governance` | Block mutations that lack valid actor/reason metadata. | 🔴 |
| `CognitiveExtractor`| `extract_facts` | Actual DSPy implementation of the FactSignature. | 🧪 |
| `WallView` | `handle_drag_promotion` | UI capability to drag a node from Forming to Frozen. | 🔴 |

## 3. Structural Gaps
- **Concurrent Writes**: `GraphManager` currently uses standard SQLite; may face locking issues under high concurrent write load from multiple agents.
- **Audit Visualization**: `phase3_audit_trace.jsonl` exists, but there is no UI component to view or filter these logs.
- **Model Agnostic Embeddings**: `VectorEmbedder` is tightly coupled to HuggingFace; needs an adapter pattern for OpenAI/Azure/Ollama.
- **Garbage Collection**: No mechanism to purge `KILLED` nodes after a certain retention period (if required).

## 4. Phase 4 Roadmap Items
1. [ ] Transition from `🧪 Mocked` signatures to `✅ Implemented` DSPy modules.
2. [ ] Connect `WallView` interactive buttons (Promote/Kill) to the `server.py` endpoints.
3. [ ] Implement the `Orchestration` verifier nodes to ensure fact consistency.
4. [ ] Build the "Audit View" for human oversight of LLM decisions.
