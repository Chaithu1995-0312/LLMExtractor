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

-- Indexes for Speed
CREATE INDEX IF NOT EXISTS idx_bricks_topic ON bricks(topic_id);
CREATE INDEX IF NOT EXISTS idx_bricks_fingerprint ON bricks(fingerprint);
CREATE INDEX IF NOT EXISTS idx_prompts_slug ON prompts(slug);
