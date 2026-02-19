-- =========================
-- SCHEMAS
-- =========================

CREATE SCHEMA IF NOT EXISTS sync;
CREATE SCHEMA IF NOT EXISTS graph;
CREATE SCHEMA IF NOT EXISTS governance;

-- =========================
-- SYNC TABLES
-- =========================

-- 1. The Compilation Scope
CREATE TABLE IF NOT EXISTS sync.topics (
    id TEXT PRIMARY KEY, -- e.g., 'nexus-server-sync'
    display_name TEXT NOT NULL,
    definition_json JSONB NOT NULL, -- The extraction policy
    ordering_rule TEXT DEFAULT 'chronological',
    state TEXT CHECK (state IN ('DRAFT', 'ACTIVE', 'LOCKED')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. The Source Artifacts
CREATE TABLE IF NOT EXISTS sync.source_runs (
    id TEXT PRIMARY KEY, -- e.g., 'run_2026_02_07'
    raw_content JSONB NOT NULL, -- The full conversation/artifact
    ingested_at TIMESTAMPTZ DEFAULT NOW(),
    status TEXT CHECK (status IN ('OPEN', 'CLOSED')),
    last_processed_index INTEGER DEFAULT -1 -- Boundary for incremental extraction
);

-- 3. The Atomic Truths
CREATE TABLE IF NOT EXISTS sync.bricks (
    id TEXT PRIMARY KEY, -- SHA-256 Hash
    topic_id TEXT REFERENCES sync.topics(id),
    
    -- Content
    content TEXT NOT NULL, -- Raw extracted text
    fingerprint TEXT NOT NULL, -- Normalized hash for dedup
    
    -- Lifecycle
    state TEXT CHECK (state IN ('IMPROVISE', 'FORMING', 'FINAL', 'SUPERSEDED')),
    superseded_by_id TEXT REFERENCES sync.bricks(id), -- Self-reference for history
    
    -- Source Tracing (The "GPS")
    run_id TEXT REFERENCES sync.source_runs(id),
    json_path TEXT NOT NULL, -- '$.messages[4].content'
    start_index INT NOT NULL,
    end_index INT NOT NULL,
    source_checksum TEXT NOT NULL, -- Data drift protection
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sync.cognitive_shards (
    id BIGSERIAL PRIMARY KEY,
    shard_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =========================
-- GRAPH TABLES
-- =========================

CREATE TABLE IF NOT EXISTS graph.nodes (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    data JSONB, -- Stores statement, lifecycle, etc.
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS graph.edges (
    id BIGSERIAL PRIMARY KEY,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    edge_type TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =========================
-- GOVERNANCE TABLES
-- =========================

-- 4. Prompt Governance
CREATE TABLE IF NOT EXISTS governance.prompts (
    slug TEXT NOT NULL, -- e.g., 'jarvis-l2-system'
    version INTEGER NOT NULL DEFAULT 1,
    content TEXT NOT NULL,
    role TEXT CHECK (role IN ('system', 'user', 'assistant')) DEFAULT 'system',
    description TEXT,
    metadata JSONB, -- Optional model-specific params
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (slug, version)
);

-- 5. Coverage Alerts (Lifecycle)
CREATE TABLE IF NOT EXISTS governance.coverage_alerts (
    alert_id TEXT PRIMARY KEY,
    fingerprint TEXT NOT NULL,
    topic_id TEXT NOT NULL,

    type TEXT NOT NULL, -- FLOW_REDUNDANCY | COVERAGE_GAP | ORPHAN_BRICKS | CONTRADICTION | LOW_SIGNAL_TOPIC
    severity TEXT NOT NULL, -- info | warning | critical
    signal_score REAL NOT NULL,

    state TEXT NOT NULL CHECK (state IN ('NEW', 'ACKNOWLEDGED', 'RESOLVED', 'DISMISSED', 'ARCHIVED')),

    summary TEXT,

    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,

    acknowledged_by TEXT,
    resolved_by TEXT,

    resolution_action TEXT,
    resolution_metadata JSONB,

    dismissed_reason TEXT,

    UNIQUE(fingerprint)
);

-- 6. Coverage Prompt Attempts
CREATE TABLE IF NOT EXISTS governance.coverage_prompt_attempts (
    id TEXT PRIMARY KEY,
    alert_id TEXT NOT NULL REFERENCES governance.coverage_alerts(alert_id),
    topic_id TEXT NOT NULL,

    prompt TEXT NOT NULL,
    attempted_at TIMESTAMPTZ NOT NULL,

    outcome TEXT CHECK (outcome IN ('SUCCESS', 'NO_DATA', 'ABORTED')),
    bricks_created INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS governance.audit_trace (
    id BIGSERIAL PRIMARY KEY,
    event_type TEXT NOT NULL,
    actor TEXT,
    payload JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =========================
-- INDEXES (CRITICAL)
-- =========================

CREATE INDEX IF NOT EXISTS idx_bricks_topic ON sync.bricks(topic_id);
CREATE INDEX IF NOT EXISTS idx_bricks_fingerprint ON sync.bricks(fingerprint);
CREATE INDEX IF NOT EXISTS idx_nodes_type ON graph.nodes(type);
CREATE INDEX IF NOT EXISTS idx_edges_source ON graph.edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON graph.edges(target_id);
CREATE INDEX IF NOT EXISTS idx_prompts_slug ON governance.prompts(slug);
CREATE INDEX IF NOT EXISTS idx_coverage_alerts_topic ON governance.coverage_alerts(topic_id);
CREATE INDEX IF NOT EXISTS idx_coverage_alerts_state ON governance.coverage_alerts(state);

-- =========================
-- VIEWS
-- =========================

CREATE OR REPLACE VIEW governance.active_alerts AS
SELECT *
FROM governance.coverage_alerts
WHERE state IN ('NEW', 'ACKNOWLEDGED');
