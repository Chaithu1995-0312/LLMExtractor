-- Phase 2: Decision Cache Implementation
-- Goal: Store LLM reasoning results to reduce redundant computation.

BEGIN;

CREATE TABLE IF NOT EXISTS graph.decision_cache (
    cache_key TEXT PRIMARY KEY,
    agent_name TEXT,
    input_hash TEXT,
    result JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    ttl_hours INT
);

CREATE INDEX IF NOT EXISTS idx_decision_cache_created_at ON graph.decision_cache(created_at);

-- Optional: Index on agent_name for analytics
CREATE INDEX IF NOT EXISTS idx_decision_cache_agent ON graph.decision_cache(agent_name);

COMMIT;
