# RULES_AND_INVARIANTS.md

This document outlines the confirmed and inferred rules, invariants, and critical assumptions governing the Nexus system and Cortex service.

## 1. Core System Invariants (Nexus)

### 1.1. Data Integrity & Consistency

- ✅ **Brick-Vector-ID Mapping Consistency:** The `brick_id`s stored in `src/nexus/vector/local_index.py` (`self.brick_ids`) *must* maintain a 1:1 positional correspondence with the vectors in the FAISS index (`self.index`) at all times. Any misalignment will lead to incorrect recall.
- ✅ **Brick Persistence:** All bricks ingested and indexed *must* have their raw content and metadata retrievable via `src/nexus/bricks/brick_store.py` based on their `brick_id`. The content in the store is the canonical source for generation.
- ✅ **FAISS Index Persistence:** The FAISS index and its associated `brick_id` mapping (`data/index/index.faiss`, `data/brick_ids.json`) *must* be correctly saved and loaded to ensure state across application restarts.
- 🟡 **Brick Status Workflow:** Bricks are expected to transition from `"PENDING"` to `"EMBEDDED"` after being added to the vector index (`src/nexus/vector/local_index.py`). This implies a state management workflow during content ingestion.

### 1.2. Semantic Recall Pipeline

- ✅ **Fixed Embedding Model:** The system *must* exclusively use the `all-MiniLM-L6-v2` SentenceTransformer model for all vector embeddings (queries and bricks) to maintain semantic consistency across the vector space (`src/nexus/vector/embedder.py`).
- ✅ **Fixed Embedding Dimension:** All embeddings *must* be 384-dimensional `float32` vectors (`src/nexus/vector/embedder.py`, `src/nexus/vector/local_index.py`).
- ✅ **Tiered Reranking Fallback:** The `RerankOrchestrator` *must* always attempt reranking in the order: LLM -> CrossEncoder -> Heuristic. It *must* gracefully fallback to the next available reranker upon failure or unavailability (`src/nexus/rerank/orchestrator.py`).
- ✅ **Heuristic Reranker Availability:** The `HeuristicReranker` *must* always be functional and available as a final fallback, as it has no external dependencies (`src/nexus/rerank/orchestrator.py`, `src/nexus/rerank/heuristic.py`).
- ✅ **Distance-to-Confidence Normalization:** Raw FAISS L2 distances *must* be transformed into a 0.0-1.0 confidence score for consistent output across the recall pipeline (`src/nexus/ask/recall.py`).
- 🟡 **Reranker Interface Consistency:** All reranker implementations (`LlmReranker`, `CrossEncoderReranker`, `HeuristicReranker`) *should* adhere to a consistent interface, accepting `(query, candidates)` and returning `candidates` with `final_score` and `reranker_used` fields.
- ✅ **Read-Only Recall (for Preview):** The `recall_bricks_readonly` function *must not* trigger any state changes or audit logging, ensuring its suitability for UI previews (`src/nexus/ask/recall.py`).

### 1.3. Module Behavior

- ✅ **Embedder Singleton:** `VectorEmbedder` *must* enforce a singleton pattern to ensure only one instance of the embedding model is loaded globally (`src/nexus/vector/embedder.py`).
- 🟡 **Global Recall State:** The `_local_index`, `_brick_store`, and `_reranker` instances in `src/nexus/ask/recall.py` are initialized globally, implying a shared, long-lived state for recall operations. Changes to this state could affect all recall calls.

## 2. Cortex Service Rules & Invariants

### 2.1. Security & Compliance

- ✅ **Mandatory Audit Logging:** Every successful call to the `/generate` endpoint *must* result in an audit record being appended to `phase3_audit_trace.jsonl`. This record *must* include `user_id`, `agent_id`, `brick_ids_used`, `model`, `token_cost`, and `timestamp` (`services/cortex/api.py`).
- ✅ **MODE-1 Enforcement (Source Reload):** For LLM-based content generation (`/generate`), the raw source text for *all* provided `brick_ids` *must* be successfully reloaded from the `BrickStore` at the time of the request. If any brick fails to reload, the generation request *must* be blocked with a "MODE-1 Violation" error (`services/cortex/api.py`). This prevents generation based on outdated or non-existent information.

### 2.2. LLM Backend Handling

- ✅ **LLM Fallback Priority:** The `/generate` endpoint *must* attempt LLM generation in the strict order: OpenAI API (if `OPENAI_API_KEY` is present) -> Local Ollama instance -> Mock fallback (`services/cortex/api.py`).
- 🟡 **Model Determinism (LLM Reranker):** The `LlmReranker` *should* maintain deterministic scoring for identical inputs by setting `seed=42` and `temperature=0.0` for LLM calls (`src/nexus/rerank/llm_reranker.py`).
- 🟡 **Model Determinism (Cross-Encoder Reranker):** The `CrossEncoderReranker` *should* maintain deterministic scoring for identical inputs by setting `torch.manual_seed(42)` (`src/nexus/rerank/cross_encoder.py`).

### 2.3. API Endpoint Behavior

- ✅ **Deterministic Routing:** The `/route` endpoint *must* use hardcoded, deterministic keyword-based rules to assign `user_query` to a specific `agent_id` and `model`. These rules are considered "LOCKED" and not subject to dynamic change based on LLM output (`services/cortex/api.py`).
- ✅ **Read-Only `/ask_preview`:** The `/ask_preview` endpoint *must* remain strictly read-only, *must not* initiate any content generation, and *must not* emit any audit records (`services/cortex/api.py`). It is solely for retrieving preliminary recall results.

## 3. General System Constraints

- 🔴 **Conflicting Audit Logs:** There are two `phase3_audit_trace.jsonl` files (`./phase3_audit_trace.jsonl` and `services/cortex/phase3_audit_trace.jsonl`). This represents a conflict in storage location or an outdated copy. The system *must* clarify which file is the canonical audit log or unify their purpose.
- 🟡 **Python Version:** The `pyproject.toml` specifies `requires-python = ">=3.8"`. The system *should* adhere to this minimum Python version.
- 🟡 **Dependencies:** All dependencies listed in `pyproject.toml` and implicitly used (e.g., `torch` for `sentence-transformers`) *must* be resolvable and installed for full functionality. Missing dependencies will lead to graceful degradation or errors in specific modules (e.g., `LlmReranker`).
- 🟡 **Local Model Availability:** The `LlmReranker` relies on the presence of a local quantized LLM model file at a specific path (`models/llama-3-8b-quantized.gguf`). The absence of this file *must* be handled as an expected failure, leading to reranker fallback (`src/nexus/rerank/llm_reranker.py`).
- 🟡 **API Key Presence:** The `CortexAPI` conditionally uses OpenAI based on the `OPENAI_API_KEY` environment variable. Its absence *must* trigger the fallback mechanism to Ollama or mock LLM (`services/cortex/api.py`).
- 🟡 **Hardcoded Paths:** Critical paths (e.g., `INDEX_PATH`, `BRICK_IDS_PATH`, default `bricks_dir`) are defined in `src/nexus/config.py`. Changes to these paths *must* be reflected consistently across the system.

## 4. Operational Invariants (Inferred)

- 🟡 **Graceful Initialization:** Components like `RerankOrchestrator`, `LlmReranker`, and `CrossEncoderReranker` are designed with `try-except` blocks during initialization to allow the system to start even if some advanced features (e.g., local LLMs, cross-encoders) are unavailable. This ensures basic functionality (heuristic reranking, mock LLM generation) is always possible.
- 🟡 **Resource Management:** Given the use of `SentenceTransformer` and potentially local LLMs, efficient memory management (e.g., singleton patterns for models) is an inferred operational invariant to prevent excessive resource consumption. (`src/nexus/vector/embedder.py`).
- 🟡 **Consistency of Confidence Scores:** While individual rerankers might use different scoring mechanisms, the final `confidence` or `final_score` presented by the recall pipeline *should* be normalized to a 0.0-1.0 range for consistent interpretation.

## 5. Security & Traceability

- ✅ **Audit Log Immutability:** Once an audit record is written to `phase3_audit_trace.jsonl`, it *must* be considered immutable. Appending is the only allowed operation. (Inferred from line-delimited JSON format and append mode writing).
- 🟡 **MODE-1 Data Source Verification:** The `_reload_source_text` mechanism for MODE-1 enforcement *should* ideally include checksums or versioning to verify that the reloaded brick content has not been tampered with or become stale since indexing, beyond just checking for existence. (🔴 GAP/ENHANCEMENT).
- 🟡 **Input Sanitization:** While not explicitly reviewed, proper input sanitization *should* be applied to all user-provided inputs (queries, user IDs, etc.) to prevent injection attacks or unexpected behavior.

## 6. Development & Maintenance Invariants

- 🟡 **Code Normalization:** All code references in documentation and discussions *should* be normalized (e.g., `src/nexus/module/file.py` or `nexus.module.file`).
- 🟡 **Uncertainty Marking:** All inferred or unconfirmed information *must* be explicitly marked with `🟡 UNCONFIRMED` or similar indicators. Conflicts *must* be marked with `🔴 CONFLICT`.
- 🟡 **Documentation Clarity:** Documentation *should* be written for both LLM interpretation and human auditing, being technically dense and free of fluff. (This rule applies to *this* documentation process).