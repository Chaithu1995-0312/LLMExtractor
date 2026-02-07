# INFERRED_ENHANCEMENTS

## 1. Architectural Evolution

- **Event Sourcing:** Since monotonic updates are core to the philosophy, migrating `GraphManager` to a full Event Sourcing model (storing events like `NODE_CREATED`, `NODE_PROMOTED` instead of just current state) would make the audit trail implicit and robust.
- **GraphRAG Integration:** The current `recall` is vector-based. Integrating graph traversal into the recall phase ("GraphRAG") could allow the system to answer questions by walking from `Topic` -> `Intent` -> `Superseded By` -> `New Intent`.

## 2. Cognitive Refinement

- **Iterative Assembly:** Currently `assemble_topic` is one-shot. An iterative loop (Agentic loop) where the LLM asks clarifying questions or requests more bricks would improve quality.
- **Self-Correction:** A background worker that periodically re-checks `LOOSE` nodes against new `FROZEN` nodes to auto-kill obsolete ideas.

## 3. User Experience

- **"Time Travel" Mode:** Since supersession preserves history, the UI could allow users to scrub a slider to see the state of knowledge at a past date.
- **Visual Diffing:** When superseding a node, show a side-by-side diff of the old statement vs. the new statement.
