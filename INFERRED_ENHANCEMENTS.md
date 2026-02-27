# INFERRED ENHANCEMENTS

## 1. Multi-Modal Ingestion
*   **Concept:** Extend `Brick` schema to support images and audio transcriptions.
*   **Rationale:** Chat logs often contain screenshots or voice memos.
*   **Implementation Path:**
    1.  Add `media_url` and `media_type` columns to `bricks` table.
    2.  Integrate a Vision LLM (e.g., GPT-4o) in `sync_agent.py` to generate text descriptions for vectors.

## 2. Dynamic Topic Discovery
*   **Concept:** Instead of a hardcoded enum `TopicID`, allow the system to propose new topics based on clustering density.
*   **Rationale:** As new domains are discussed (e.g., "Quantum Computing"), the system should adapt without code changes.
*   **Implementation Path:**
    1.  Create a "Topic Proposal" table.
    2.  Run a nightly job analyzing "Unclassified" Bricks.
    3.  If a dense cluster (> 50 bricks) is found, propose a new Topic to the admin.

## 3. Cognitive "Sleep" Cycles
*   **Concept:** A dedicated nightly process for deep graph optimization.
*   **Rationale:** Expensive operations like global Entity Resolution and Graph Re-indexing degrade real-time query performance.
*   **Implementation Path:**
    1.  Schedule `maintenance_worker` to run at 3 AM.
    2.  Perform aggressive graph compaction, orphan removal, and index rebuilding during this window.
