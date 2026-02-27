# GAPS AND TODOS

## 1. Critical Gaps (P0)

### 1.1 L3 Sage Implementation Missing
*   **Gap:** The `L3Sage` class is defined in architecture but the implementation file `src/nexus/cognition/l3_sage.py` is largely empty or skeletal.
*   **Impact:** Deep reasoning tasks cannot be orchestrated; the system is limited to L1 (Ingest) and L2 (Compile) thinking.
*   **Action:** Implement `orchestrate_deep_thought()` with async Task Queue integration.

### 1.2 Entity Resolution is Mocked
*   **Gap:** `EntityResolver.resolve()` currently uses simplistic string matching or is stubbed out.
*   **Impact:** Duplicate nodes (e.g., "Python" vs "Python 3") proliferate, degrading graph quality.
*   **Action:** Integrate LLM-based disambiguation with a "human-in-the-loop" review queue.

## 2. Important Improvements (P1)

### 2.1 Topic Router Optimization
*   **Gap:** `TopicRouter` relies too heavily on simple keywords.
*   **Action:** Fine-tune a small classifier model (or use few-shot prompting) for higher accuracy routing of ambiguous Bricks.

### 2.2 Lack of Garbage Collection
*   **Gap:** Deleted Bricks leave orphaned Embeddings in `pgvector`.
*   **Action:** Implement a `compaction_worker` to clean up unreferenced vectors during off-peak hours.

## 3. Tech Debt & Maintenance
*   **Test Coverage:** Unit tests for `promotion_engine.py` are missing.
*   **Hardcoded Configuration:** embedding dimensions and model names are scattered across SQL and Python files. Centralize in `src/nexus/config.py`.
