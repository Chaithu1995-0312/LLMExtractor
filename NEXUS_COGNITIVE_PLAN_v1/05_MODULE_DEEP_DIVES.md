# Module Deep Dives — Nexus

## Conversation Index Builder
Purpose:
Create a stable index mapping conversation identity to human-readable metadata.

Key Fields:
- chat_id
- title (deterministic)
- created_at / updated_at
- content_hash
- source_file

Supports incremental ingestion and UI decoration.

## Cognition Assembler
Function:
assemble_topic(topic_query)

Pipeline:
1. Recall bricks
2. Expand to full conversations
3. Deduplicate by content hash
4. Assemble canonical JSON
5. Persist artifact
6. Register graph edges

No inference. No summarization.
