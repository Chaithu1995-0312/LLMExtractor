# Inferred Enhancements

## 1. Graph-Driven RAG (The "Anchor" Loop)
The presence of "Hard Anchors" and "Soft Anchors" in the Graph data structure suggests a powerful feedback loop:
*   **Current**: User searches $\rightarrow$ Recalls Bricks $\rightarrow$ Manually Promotes to Anchor.
*   **Enhancement**: **Anchor-Biased Retrieval**. When a user queries a concept (e.g., "Architecture"), the system should *automatically* retrieve all "Hard Anchored" bricks for that concept *before* performing vector search. This guarantees that human-curated knowledge always trumps probabilistic search.

## 2. Dynamic Wall Construction
The `nexus wall` command builds static token blocks.
*   **Enhancement**: **Just-in-Time Walls**. Instead of pre-building walls, allow Cortex to request a "Wall of Context" for a specific time range or topic dynamically.
*   **Use Case**: "Summarize my coding work from last week". Nexus assembles a 100k token wall of all coding-related bricks from that timespan on the fly.

## 3. Local LLM Integration
The architecture is designed for "Offline Sovereignty".
*   **Enhancement**: Integrate `ollama` or `llama.cpp` directly into `CortexAPI`.
*   **Benefit**: Full privacy. No data leaves the machine, even for generation. The "Simulated Response" can be replaced by Llama-3-8B running locally.

## 4. Visual Graph Editing
The UI supports "Promote/Reject".
*   **Enhancement**: Full Graph CRUD. Allow users to create new Concept Nodes and draw edges directly in the Jarvis UI.
*   **Impact**: Turns Jarvis from a passive viewer into an active "Knowledge Gardener" tool.

## 5. Multi-Modal Bricks
Current extractors focus on text.
*   **Enhancement**: Parse image attachments from `conversations.json` (if available in export) and store them as "Image Bricks" with CLIP embeddings.
