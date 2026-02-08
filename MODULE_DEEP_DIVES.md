# Module Deep Dives

## 1. Graph Manager (`src/nexus/graph/manager.py`)
**Role:** The Central Nervous System. Manages the unified graph of Intent, Source, Scope, and Brick nodes.

### Method: `promote_node_to_frozen(node_id, promote_bricks, actor)`
*   **Responsibility:** Executes the critical lifecycle transition from `FORMING` to `FROZEN`.
*   **Inputs:**
    *   `node_id` (str): UUID of the node to freeze.
    *   `promote_bricks` (List[str]): IDs of bricks acting as "Hard Anchors".
    *   `actor` (str): ID of the user/agent authorizing the freeze.
*   **Outputs:** None (State change).
*   **Invariants Enforced:**
    *   Node must currently be in `FORMING` state.
    *   Transition is monotonic (cannot go back to LOOSE).
*   **Side Effects:**
    *   Updates `nodes` table (lifecycle="frozen", hard_anchors=...).
    *   Logs `NODE_FROZEN` event to Audit Trace.
    *   Emits `NODE_FROZEN` pulse to Gateway.
*   **Failure Modes:**
    *   `ValueError`: If node not found or not in `FORMING` state.
*   **Lifecycle:** **GATEKEEPER** (Write Barrier).

### Method: `supersede_node(old_node_id, new_node_id, reason, actor)`
*   **Responsibility:** Replaces an obsolete fact with a new one while preserving history.
*   **Inputs:** `old_node_id`, `new_node_id`, `reason`, `actor`.
*   **Invariants Enforced:**
    *   Both nodes must be `FROZEN`.
    *   Nodes cannot supersede themselves.
*   **Side Effects:**
    *   Creates edge: `old -> [SUPERSEDED_BY] -> new`.
    *   Updates `nodes` metadata: `old.superseded_by`, `new.supersedes`.
    *   Logs `NODE_SUPERSEDED` event.
*   **Lifecycle:** **GOVERNANCE** (History Preservation).

---

## 2. Nexus Compiler (`src/nexus/sync/compiler.py`)
**Role:** The Zero-Trust Ingestion Engine. Transforms raw logs into verified Bricks.

### Method: `compile_run(run_id, topic_id)`
*   **Responsibility:** Orchestrates the extraction pipeline for a specific conversation run.
*   **Control Flow:**
    1.  **Fetch:** Retrieves Run JSON and Topic Definition from DB.
    2.  **Scan:** Calls `_pre_filter_nodes` to optimize context.
    3.  **LLM:** Calls `_llm_extract_pointers` to get candidate quotes.
    4.  **Validate:** Calls `_materialize_brick` for byte-level verification.
    5.  **Persist:** Saves valid bricks to DB.
*   **Outputs:** Integer (count of new bricks).

### Method: `_materialize_brick(run_data, run_id, pointer, topic_id)`
*   **Responsibility:** The "Zero-Trust Gate". Validates that the LLM's hallucinated pointer matches reality.
*   **Inputs:** Raw JSON data, pointer object (JSONPath + Verbatim Quote).
*   **Logic:**
    1.  Resolves JSONPath to find the node text.
    2.  Searches for `verbatim_quote` within that text.
    3.  **CRITICAL:** If quote is missing, returns `None` (Silent Rejection).
*   **Outputs:** `Brick` dict or `None`.
*   **Invariants Enforced:** Content MUST exist in source.
*   **Security:** Prevents "hallucinated facts" from entering the graph.

---

## 3. Cortex Gateway (`services/cortex/gateway.py`)
**Role:** The Economic Router. Manages cognitive costs.

### Method: `pulse(event_type, context)` (Tier L1)
*   **Responsibility:** Low-cost system narration.
*   **Routing:** Directs request to **Local LLM** (Ollama/Llama3).
*   **Cost:** $0.00.
*   **Fallbacks:** Returns static string if local inference fails.

### Method: `explain(query, context_bricks)` (Tier L2)
*   **Responsibility:** High-quality user Q&A.
*   **Routing:** Directs request to **LiteLLM Proxy** (Claude-3.5 Sonnet).
*   **Cost:** ~$0.01 per call.
*   **Logic:**
    1.  Injects "Governor" system prompt.
    2.  Checks for proxy errors (429 Budget Exceeded).
    3.  Returns content + usage stats.
*   **Lifecycle:** **Read-Only** (does not write to graph).

---

## 4. Vector Embedder (`src/nexus/vector/embedder.py`)
**Role:** Semantic Indexing.

### Method: `embed_query(query, use_genai)`
*   **Responsibility:** Converts text to vector.
*   **Inputs:** `query` (str), `use_genai` (bool).
*   **Logic:**
    1.  (Optional) Calls `_rewrite_with_llm` to expand technical terms (e.g., "brick" -> "nexus documentation unit").
    2.  Calls `SentenceTransformer.encode`.
*   **Outputs:** `numpy.ndarray` (384-d).
*   **Performance:** Singleton pattern ensures model is loaded once.
