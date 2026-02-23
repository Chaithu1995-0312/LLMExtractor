-- Migration: Add graph.cognition_logs table
-- Purpose: Persistent storage for L2 (Narrator) and L3 (Sage) outputs.
-- Invariants: Strictly append-only logging. No updates to existing logs.

CREATE TABLE IF NOT EXISTS graph.cognition_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    layer TEXT NOT NULL CHECK (layer IN ('L2', 'L3')),
    topic_id TEXT NULL,
    cluster_id TEXT NULL,

    trigger_event TEXT, -- e.g., 'SUPERCESSION_APPROVED', 'WEEKLY_AUDIT', 'MANUAL_QUERY'
    
    input_snapshot_hash TEXT NOT NULL, -- Merkle root or hash of the graph state used for input

    prompt_text TEXT NOT NULL,
    output_text TEXT NOT NULL,

    model_used TEXT NOT NULL,
    confidence_score FLOAT CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    
    latency_ms INT,
    token_usage INT,

    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_cognition_logs_layer ON graph.cognition_logs(layer);
CREATE INDEX IF NOT EXISTS idx_cognition_logs_topic ON graph.cognition_logs(topic_id);
CREATE INDEX IF NOT EXISTS idx_cognition_logs_created_at ON graph.cognition_logs(created_at DESC);
