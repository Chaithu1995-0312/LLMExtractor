-- =========================
-- EVOLUTION LAYER (Drift & Candidates)
-- =========================

-- 1. Edge Candidates (Suggestions from Drift Engine)
CREATE TABLE IF NOT EXISTS graph.edge_candidates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    source_intent_id TEXT NOT NULL REFERENCES graph.nodes(id) ON DELETE CASCADE,
    target_intent_id TEXT NOT NULL REFERENCES graph.nodes(id) ON DELETE CASCADE,

    suggested_edge_type TEXT NOT NULL, -- REFINES, SUPERSEDES, CONFLICTS_WITH
    similarity_score FLOAT NOT NULL,
    drift_score FLOAT NOT NULL,
    confidence_score FLOAT NOT NULL,

    status TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED')),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by TEXT NOT NULL DEFAULT 'system-drift-engine',

    reviewed_at TIMESTAMPTZ,
    reviewed_by TEXT,

    -- Prevent duplicate suggestions for the same pair and type
    UNIQUE(source_intent_id, target_intent_id, suggested_edge_type)
);

-- 2. Vector Metadata (Model Versioning)
CREATE TABLE IF NOT EXISTS graph.vector_meta (
    node_id TEXT PRIMARY KEY REFERENCES graph.nodes(id) ON DELETE CASCADE,

    embedding_model TEXT NOT NULL,
    embedding_version TEXT NOT NULL,
    indexed_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Cluster Statistics (Evolution Metrics)
CREATE TABLE IF NOT EXISTS graph.cluster_stats (
    cluster_id TEXT PRIMARY KEY,
    
    node_count INTEGER NOT NULL DEFAULT 0,
    edge_count INTEGER NOT NULL DEFAULT 0,
    supersession_depth INTEGER NOT NULL DEFAULT 0,
    
    volatility FLOAT NOT NULL DEFAULT 0.0,
    stability_index FLOAT NOT NULL DEFAULT 0.0,
    conflict_ratio FLOAT NOT NULL DEFAULT 0.0,
    
    last_computed_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Global System Statistics (Time-series Snapshots)
CREATE TABLE IF NOT EXISTS graph.system_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    total_nodes INTEGER NOT NULL,
    total_edges INTEGER NOT NULL,
    
    total_candidates INTEGER NOT NULL,
    approved_candidates INTEGER NOT NULL,
    rejected_candidates INTEGER NOT NULL,
    approval_ratio FLOAT NOT NULL,
    
    supersession_edges INTEGER NOT NULL,
    conflict_edges INTEGER NOT NULL,
    
    average_pending_age_hours FLOAT NOT NULL,
    
    computed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_system_stats_date ON graph.system_stats(computed_at);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_edge_candidates_status ON graph.edge_candidates(status);
CREATE INDEX IF NOT EXISTS idx_edge_candidates_source ON graph.edge_candidates(source_intent_id);
