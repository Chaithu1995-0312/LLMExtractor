# Appendix

## A. Data Schemas

### 1. Brick Schema
```json
{
  "brick_id": "sha256...",
  "source_file": "/abs/path/to/source.json",
  "source_span": {
    "message_id": "uuid",
    "block_index": 0,
    "text_sample": "First 50 chars..."
  },
  "intent": "atomic_content",
  "tags": [],
  "scope": "PRIVATE",
  "status": "PENDING | EMBEDDED",
  "content": "Full text content...",
  "hash": "sha256(content)"
}
```

### 2. Cognition Artifact Schema
```json
{
  "artifact_id": "sha256...",
  "created_at": "ISO8601",
  "query": "Topic Name",
  "derived_from": ["brick_id_1", "brick_id_2"],
  "payload": {
    "topic": "Topic Name",
    "provenance": { ... },
    "raw_excerpts": [ ... ],
    "extracted_facts": ["Fact 1", "Fact 2"],
    "visuals": { "mermaid": "...", "latex": "..." },
    "artifact_type": "TOPIC_COGNITION_V1"
  }
}
```

### 3. Graph Node Types
| Type | Description |
| :--- | :--- |
| `intent` | An atomic fact or assertion extracted from bricks. |
| `topic` | A high-level cluster concept (e.g., "Docker Deployment"). |
| `artifact` | The JSON document representing the assembled topic. |
| `brick` | A reference to the raw data segment. |
| `source` | A reference to the original file. |

### 4. Graph Edge Types
| Type | Source | Target | Description |
| :--- | :--- | :--- | :--- |
| `ASSEMBLED_IN` | Topic | Artifact | Artifact belongs to topic history. |
| `DERIVED_FROM` | Artifact | Brick | Artifact used this brick. |
| `OVERRIDES` | Intent | Intent | Source supersedes Target (Monotonicity). |
| `APPLIES_TO` | Intent | Scope | Intent is valid within this scope. |

## B. Directory Structure
```
d:\chatgptdocs\
├── data\
│   ├── bricks\         # Extracted JSON bricks
│   ├── index\          # FAISS index files
│   └── history\        # Raw conversation trees
├── output\
│   └── artifacts\      # Assembled cognition JSONs
├── src\
│   └── nexus\          # Core logic
└── services\
    └── cortex\         # API layer
```

## C. System Environment
-   **Python**: 3.10+
-   **Vector DB**: FAISS (via `faiss-cpu` or `faiss-gpu`)
-   **Graph DB**: SQLite 3
-   **LLM Interface**: DSPy (configured for OpenAI or similar)
