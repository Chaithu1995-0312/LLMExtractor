-- 1. The Compilation Scope
CREATE TABLE IF NOT EXISTS topics (
    id TEXT PRIMARY KEY, -- e.g., 'nexus-server-sync'
    display_name TEXT NOT NULL,
    definition_json JSON NOT NULL, -- The extraction policy
    ordering_rule TEXT DEFAULT 'chronological',
    state TEXT CHECK (state IN ('DRAFT', 'ACTIVE', 'LOCKED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. The Source Artifacts
CREATE TABLE IF NOT EXISTS source_runs (
    id TEXT PRIMARY KEY, -- e.g., 'run_2026_02_07'
    raw_content JSON NOT NULL, -- The full conversation/artifact
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT CHECK (status IN ('OPEN', 'CLOSED')),
    last_processed_index INTEGER DEFAULT -1 -- Boundary for incremental extraction
);

-- 3. The Atomic Truths
CREATE TABLE IF NOT EXISTS bricks (
    id TEXT PRIMARY KEY, -- SHA-256 Hash
    topic_id TEXT REFERENCES topics(id),
    
    -- Content
    content TEXT NOT NULL, -- Raw extracted text
    fingerprint TEXT NOT NULL, -- Normalized hash for dedup
    
    -- Lifecycle
    state TEXT CHECK (state IN ('IMPROVISE', 'FORMING', 'FINAL', 'SUPERSEDED')),
    superseded_by_id TEXT REFERENCES bricks(id), -- Self-reference for history
    
    -- Source Tracing (The "GPS")
    run_id TEXT REFERENCES source_runs(id),
    json_path TEXT NOT NULL, -- '$.messages[4].content'
    start_index INT NOT NULL,
    end_index INT NOT NULL,
    source_checksum TEXT NOT NULL, -- Data drift protection
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Prompt Governance
CREATE TABLE IF NOT EXISTS prompts (
    slug TEXT NOT NULL, -- e.g., 'jarvis-l2-system'
    version INTEGER NOT NULL DEFAULT 1,
    content TEXT NOT NULL,
    role TEXT CHECK (role IN ('system', 'user', 'assistant')) DEFAULT 'system',
    description TEXT,
    metadata JSON, -- Optional model-specific params
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (slug, version)
);

-- 5. Coverage Alerts (Lifecycle)
CREATE TABLE IF NOT EXISTS coverage_alerts (
    alert_id TEXT PRIMARY KEY,
    fingerprint TEXT NOT NULL,
    topic_id TEXT NOT NULL,

    type TEXT NOT NULL, -- FLOW_REDUNDANCY | COVERAGE_GAP | ORPHAN_BRICKS | CONTRADICTION | LOW_SIGNAL_TOPIC
    severity TEXT NOT NULL, -- info | warning | critical
    signal_score REAL NOT NULL,

    state TEXT NOT NULL CHECK (state IN ('NEW', 'ACKNOWLEDGED', 'RESOLVED', 'DISMISSED', 'ARCHIVED')),

    summary TEXT,

    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    acknowledged_by TEXT,
    resolved_by TEXT,

    resolution_action TEXT,
    resolution_metadata JSON,

    dismissed_reason TEXT,

    UNIQUE(fingerprint)
);

-- 6. Coverage Prompt Attempts
CREATE TABLE IF NOT EXISTS coverage_prompt_attempts (
    id TEXT PRIMARY KEY,
    alert_id TEXT NOT NULL,
    topic_id TEXT NOT NULL,

    prompt TEXT NOT NULL,
    attempted_at TEXT NOT NULL,

    outcome TEXT CHECK (outcome IN ('SUCCESS', 'NO_DATA', 'ABORTED')),
    bricks_created INTEGER DEFAULT 0,

    FOREIGN KEY(alert_id) REFERENCES coverage_alerts(alert_id)
);

-- Indexes for Speed
CREATE INDEX IF NOT EXISTS idx_bricks_topic ON bricks(topic_id);
CREATE INDEX IF NOT EXISTS idx_bricks_fingerprint ON bricks(fingerprint);
CREATE INDEX IF NOT EXISTS idx_prompts_slug ON prompts(slug);
CREATE INDEX IF NOT EXISTS idx_coverage_alerts_topic ON coverage_alerts(topic_id);
CREATE INDEX IF NOT EXISTS idx_coverage_alerts_state ON coverage_alerts(state);

-- Views
CREATE VIEW IF NOT EXISTS active_alerts AS
SELECT *
FROM coverage_alerts
WHERE state IN ('NEW', 'ACKNOWLEDGED');
