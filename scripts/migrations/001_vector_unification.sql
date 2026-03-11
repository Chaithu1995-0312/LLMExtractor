-- Phase 1: Prepare for Vector Unification
-- Goal: Add support for 1536-dim vectors alongside existing ones.

BEGIN;

-- Ensure vector_meta has the correct structure for versioned embeddings
-- We add embedding_v2 for the new 1536-dim vectors.
-- The existing 'embedding' column might be 1536 (from backfill) or 768 (if any legacy local stuff wrote to it).
-- To be safe, we treat 'embedding_v2' as the target for the unified 1536 model.

ALTER TABLE graph.vector_meta
    ADD COLUMN IF NOT EXISTS embedding_v2 vector(1536),
    ADD COLUMN IF NOT EXISTS embedding_model_v2 TEXT DEFAULT 'text-embedding-3-small';

-- Verify indices exist for performance
CREATE INDEX IF NOT EXISTS idx_vector_meta_node_id ON graph.vector_meta(node_id);

COMMIT;
