# Rules & Invariants — Nexus

## Memory Rules
- Brick size cap MUST remain enforced in embedder.py
- No summarization at ingestion, recall, or assembly
- Embeddings are indexing hints, not knowledge stores

## Sync Rules
- Sync must be incremental and idempotent
- Old conversations must never be reprocessed
- New uploads must append only

## Cognition Rules
- Topic assembly must reread raw source documents
- Artifacts must be deterministic and immutable
- If recall finds nothing, artifact still created with coverage_status=NO_RECALL_MATCHES

## Agent Rules
- Agents must consume artifacts only
- Agents must cite provenance (chat → message → block)
- Agents must not perform recall themselves
