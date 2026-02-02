# Appendix

## A. JSON Schemas

### 1. Brick Structure (`output/nexus/bricks/*.json`)
```json
{
  "brick_id": "string (uuid)",
  "source_file": "string (path to tree json)",
  "source_span": {
    "message_id": "string",
    "block_index": "integer"
  },
  "content": "string (text content)",
  "status": "PENDING | EMBEDDED"
}
```

### 2. Graph Node (`nexus/graph/nodes.json`)
```json
[
  {
    "id": "string (unique)",
    "label": "string (display name)",
    "anchors": {
      "hard": ["string (brick_id)"],
      "soft": ["string (brick_id)"]
    }
  }
]
```

### 3. Graph Edge (`nexus/graph/edges.json`)
```json
[
  {
    "source": "string (node_id)",
    "target": "string (node_id)",
    "type": "string (relation label)"
  }
]
```

### 4. Tree Path (`output/nexus/trees/.../*.json`)
```json
{
  "conversation_id": "string",
  "title": "string",
  "tree_path_id": "string (root>child>child)",
  "messages": [
    {
      "message_id": "string",
      "role": "user | assistant",
      "content": "string",
      "model_name": "string",
      "created_at": "string (iso8601)"
    }
  ]
}
```

## B. Configuration Constants
*(Inferred from code)*

-   **Vector Dimension**: `384` (`local_index.py`)
-   **Wall Token Limit**: `32000` (`walls/builder.py`)
-   **API Port**: `5001` (`server.py`)
