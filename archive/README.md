# Nexus Archive

This directory contains inactive reference implementations. 

## Archived Modules

### `nexus/graph/neo4j_manager.py`
- **Original Intent**: Neo4j driver for the Knowledge Graph.
- **Reason for Archival**: System standardized on `sqlite3` (src/nexus/graph/manager.py) for reduced operational complexity.
- **Status**: Dead code. Do not import.

### `nexus/vector/pinecone_index.py`
- **Original Intent**: Cloud-native Pinecone vector store.
- **Reason for Archival**: System uses `FAISS` (src/nexus/vector/local_index.py) for local-first, zero-cost operation.
- **Status**: Dead code. Do not import.
