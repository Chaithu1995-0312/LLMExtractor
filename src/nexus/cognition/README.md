# Nexus Cognition Pipeline

This module provides the `assemble_topic` pipeline for high-integrity knowledge assembly.

## Agent Consumption Rules (NON-NEGOTIABLE)

**SYSTEM RULES (NEXUS COGNITION):**

You are operating on a Nexus cognition artifact.
This artifact is lossless, canonical, and immutable.

Rules:
- Do NOT perform vector search or recall.
- Do NOT summarize unless explicitly asked.
- Do NOT invent information.
- All reasoning must reference artifact content.
- When stating facts, cite source_file + message_id + block_index.
- If information is missing, state "NOT PRESENT IN ARTIFACT".

You must treat the artifact as the sole source of truth.

## Consumption Contract

LLM Agents must ONLY consume the JSON artifacts produced by `nexus.cognition.assemble_topic`.
Agents must NEVER query the vector index directly for knowledge generation.

### Artifact Schema

```json
{
  "artifact_id": "sha256:...",
  "created_at": "ISO-8601 timestamp",
  "query": "original topic query",
  "derived_from": ["brick_id_1", "brick_id_2"],
  "payload": {
    "topic": "...",
    "artifact_type": "TOPIC_COGNITION_V1",
    "coverage_status": "ASSEMBLED",
    "provenance": {
      "brick_ids": [...],
      "source_files": [...]
    },
    "raw_excerpts": [
      {
        "source_file": "path/to/source.json",
        "coverage": {
          "spans": [
            { "message_id": "msg_1", "block_index": 2 }
          ]
        },
        "conversation": [
          {
            "message_id": "msg_1",
            "role": "user",
            "created_at": "...",
            "blocks": [
                { "index": 0, "text": "..." },
                { "index": 1, "text": "..." }
            ]
          },
          ...
        ]
      }
    ],
    "extracted_facts": [],
    "decisions": [],
    "constraints": [],
    "edge_cases": []
  }
}
```

## Failure Modes & Safeguards

1.  **Missing Source Files**:
    *   **Mode**: A brick points to a source file that has been moved or deleted.
    *   **Safeguard**: The assembler logs an error (`ERROR: Failed to load source...`) and skips that specific document, proceeding with others. The pipeline does not crash.

2.  **Corrupt Source Files**:
    *   **Mode**: A source file is not valid JSON.
    *   **Safeguard**: `json.load` failure is caught, logged, and the document is skipped.

3.  **Empty Recall**:
    *   **Mode**: No bricks match the query.
    *   **Safeguard**: An artifact is produced with `coverage_status: "NO_RECALL_MATCHES"` and empty `raw_excerpts`, providing an explicit signal of no data.

4.  **Memory Overload**:
    *   **Mode**: `recall_bricks` returns too many distinct large documents.
    *   **Safeguard**: `recall_bricks` `k` parameter caps the number of bricks (default 15). Each unique document is loaded only once regardless of how many bricks point to it.

5.  **Deduplication Collisions**:
    *   **Mode**: Different file paths point to identical content (e.g. copies).
    *   **Safeguard**: Content-based hashing (SHA256 of the loaded tree) ensures only one copy of any unique document content is included in the output.

## Invariants

-   **Read-Only**: The pipeline uses `recall_bricks_readonly` to ensure no side effects on the index.
-   **No Truncation**: Full conversations are always loaded.
-   **Immutability**: Artifacts are content-addressed and never modified after creation.
-   **Time-Independence**: The artifact payload (and its hash) does not contain timestamps, ensuring stable addressing.
