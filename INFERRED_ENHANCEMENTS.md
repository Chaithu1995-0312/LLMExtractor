# NEXUS INFERRED ENHANCEMENTS

## 1. Cognitive Enhancements 🧪
- **Recursive Extraction:** The `CognitiveExtractor` could be enhanced to perform recursive extraction. If a fact is found that mentions a new entity, the system could automatically trigger a new extraction pass on all bricks related to that entity.
- **Sentiment & Meta-Cognition:** Adding a `SentimentSignature` to DSPy modules to track user frustration or urgency, allowing the `route` method in `CortexAPI` to prioritize certain queries.
- **Cross-Topic Synthesis:** Currently, synthesis is mostly topic-bound. An inferred enhancement is a "Global Synthesizer" that looks for relationships between distant topics (e.g., how a technical requirement in Topic A impacts a business goal in Topic B).

## 2. Infrastructure & Scaling 🔴
- **Distributed Vector Search:** As the number of Bricks grows, the `LocalVectorIndex` (FAISS) may become a memory bottleneck. An inferred migration to a dedicated vector database (e.g., Qdrant or Milvus) is likely necessary.
- **Event-Driven Sync:** Instead of periodic "Sync Runs", the system could move to an event-driven model using a message queue (e.g., RabbitMQ or Redis Streams), where new data is "Brickified" immediately upon arrival.
- **Multi-Tenant Scoping:** The current `ScopeNode` implementation is flat. It can be enhanced into a hierarchical multi-tenant system where `Organization` -> `Project` -> `Session` scopes are strictly inherited and enforced.

## 3. UX & Observability 🟡
- **Interactive Graph Projection:** The `WallView` in the UI could allow users to manually draw edges that are then "Verified" by the `Cognition` layer, creating a hybrid human-AI knowledge loop.
- **Causal Audit Trails:** Enhancing the audit log to include "Why" a decision was made by capturing the full DSPy trace (including prompt and LLM raw output) for every `register_node` call.
- **Self-Healing Index:** A background task that monitors search precision and automatically triggers a `rebuild_vector_index` if query-to-result relevance drops below a threshold.

## 4. Governance & Security 🧪
- **Differential Privacy in Recall:** When retrieving Bricks for an LLM prompt, the system could automatically redact PII (Personally Identifiable Information) using an inferred `RedactionModule`.
- **Policy-Based Graph Access:** Moving from simple scopes to an Attribute-Based Access Control (ABAC) system for the Knowledge Graph.
- **AI Explanation Contract:** Expanding the `ai_explanation_contract.md` into a runtime enforcement engine that blocks LLM outputs that don't meet strict structural or safety criteria.
