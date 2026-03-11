-- Phase 3: Goal Engine Implementation
-- Goal: Enable autonomous, long-lived objectives for the cognitive system.

BEGIN;

CREATE TABLE IF NOT EXISTS graph.goals (
    goal_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    description TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PENDING', 'ACTIVE', 'BLOCKED', 'COMPLETED', 'FAILED')),
    priority INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_goals_status_priority ON graph.goals(status, priority DESC);
CREATE INDEX IF NOT EXISTS idx_goals_updated_at ON graph.goals(updated_at);

COMMIT;
