-- Production Schema for Jarvis UI (System of Record)

CREATE TABLE IF NOT EXISTS intents (
    id TEXT PRIMARY KEY,
    title TEXT,
    lifecycle TEXT DEFAULT 'FORMING',
    confidence FLOAT DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS nodes (
    id SERIAL PRIMARY KEY,
    intent_id TEXT REFERENCES intents(id) ON DELETE CASCADE,
    json_path TEXT,
    verbatim_quote TEXT,
    fingerprint TEXT,
    source_run_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS edges (
    id SERIAL PRIMARY KEY,
    from_intent TEXT REFERENCES intents(id) ON DELETE CASCADE,
    to_intent TEXT REFERENCES intents(id) ON DELETE CASCADE,
    edge_type TEXT,
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS runs (
    id SERIAL PRIMARY KEY,
    run_id TEXT UNIQUE,
    s3_key TEXT,
    status TEXT DEFAULT 'PENDING',
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indices for performance
CREATE INDEX IF NOT EXISTS idx_nodes_intent_id ON nodes(intent_id);
CREATE INDEX IF NOT EXISTS idx_edges_from_intent ON edges(from_intent);
CREATE INDEX IF NOT EXISTS idx_edges_to_intent ON edges(to_intent);
