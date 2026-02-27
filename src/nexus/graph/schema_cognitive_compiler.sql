-- =============================================================================
-- COGNITIVE COMPILER SCHEMA — v1.0
-- Structured Knowledge Compiler + Governance Extension
--
-- Adds:
--   1. entity_aliases          — alias store for EntityResolver
--   2. topic_snapshots         — deterministic versioned document store
--   3. drift_reports           — advisory-only Refiner output
--   4. ontology enforcement    — IS_SUBTOPIC_OF tracking via graph.nodes/edges
--
-- All statements are idempotent (IF NOT EXISTS).
-- NEVER modifies existing tables in a destructive way.
-- NEVER modifies graph.nodes or graph.edges core columns.
-- =============================================================================

-- =============================================================================
-- SECTION 1 — ENTITY RESOLVER ALIAS TABLE
--
-- Stores canonical aliases for known FROZEN nodes so EntityResolver can
-- detect duplicates before a new node is created.
-- Write-path: Only GraphManager.register_node() may add aliases.
-- Read-path: EntityResolver.resolve() scans this table.
-- =============================================================================

CREATE TABLE IF NOT EXISTS cognition.entity_aliases (
    id          UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id     TEXT    NOT NULL,                   -- FK-style reference to graph.nodes.id
    alias_text  TEXT    NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (node_id, alias_text)
);

-- Fast lookup by alias text (used in exact + fuzzy pre-filter)
CREATE INDEX IF NOT EXISTS idx_entity_aliases_text
    ON cognition.entity_aliases (alias_text);

-- Lookup by node (e.g. fetch all aliases for a given canonical node)
CREATE INDEX IF NOT EXISTS idx_entity_aliases_node
    ON cognition.entity_aliases (node_id);

-- =============================================================================
-- SECTION 2 — TOPIC SNAPSHOT VERSIONING
--
-- Each compile_topic_document run optionally persists its output here.
-- Version numbering follows semver (major.minor.patch as TEXT for flexibility).
-- Idempotent insert: ON CONFLICT DO NOTHING on (topic_id, version).
-- =============================================================================

CREATE TABLE IF NOT EXISTS cognition.topic_snapshots (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_id        TEXT        NOT NULL,
    version         TEXT        NOT NULL,           -- e.g. "1.0.0", "1.1.0"
    document_hash   TEXT        NOT NULL,           -- SHA-256 of canonical JSON
    document_json   JSONB       NOT NULL,           -- full StructuredDocument payload
    section_count   INTEGER     NOT NULL DEFAULT 0,
    intent_count    INTEGER     NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (topic_id, version)
);

-- Latest snapshot per topic — most common query pattern
CREATE INDEX IF NOT EXISTS idx_topic_snapshots_topic_created
    ON cognition.topic_snapshots (topic_id, created_at DESC);

-- Hash deduplication check — used to detect unchanged compilations
CREATE INDEX IF NOT EXISTS idx_topic_snapshots_hash
    ON cognition.topic_snapshots (document_hash);

-- =============================================================================
-- SECTION 3 — DRIFT REPORTS (Advisory Only)
--
-- Safe Refiner writes advisory drift reports here.
-- INVARIANT: Refiner NEVER calls supersede_node() or kill_node().
-- This table is READ-ONLY from a governance perspective.
-- =============================================================================

CREATE TABLE IF NOT EXISTS cognition.drift_reports (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_id        TEXT,                           -- Topic context (nullable for node-level reports)
    node_id         TEXT        NOT NULL,           -- Primary node under scrutiny
    issue_type      TEXT        NOT NULL,           -- e.g. 'embedding_distance_shift', 'contradictory_edge'
    severity        FLOAT       NOT NULL DEFAULT 0.0
                                CHECK (severity >= 0.0 AND severity <= 1.0),
    related_nodes   JSONB       NOT NULL DEFAULT '[]', -- Array of related node_ids
    description     TEXT,                           -- Human-readable advisory
    resolved        BOOLEAN     NOT NULL DEFAULT FALSE,
    resolved_at     TIMESTAMPTZ,
    resolved_by     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Per-topic recent drift reports
CREATE INDEX IF NOT EXISTS idx_drift_reports_topic
    ON cognition.drift_reports (topic_id, created_at DESC)
    WHERE topic_id IS NOT NULL;

-- Per-node drift history
CREATE INDEX IF NOT EXISTS idx_drift_reports_node
    ON cognition.drift_reports (node_id, created_at DESC);

-- Unresolved reports — primary Refiner queue view
CREATE INDEX IF NOT EXISTS idx_drift_reports_unresolved
    ON cognition.drift_reports (severity DESC, created_at DESC)
    WHERE resolved = FALSE;

-- =============================================================================
-- SECTION 4 — ONTOLOGY GOVERNANCE HELPER VIEW
--
-- Surfaces all Topic nodes and their Ontology parent via IS_SUBTOPIC_OF edges.
-- Read-only view; no new tables needed — leverages existing graph.nodes + graph.edges.
-- =============================================================================

CREATE OR REPLACE VIEW cognition.topic_ontology_map AS
    SELECT
        t.id            AS topic_id,
        t.data->>'name' AS topic_name,
        e.target_id     AS ontology_id,
        o.data->>'name' AS ontology_name,
        e.created_at    AS linked_at
    FROM graph.nodes t
    JOIN graph.edges e
        ON t.id = e.source_id
        AND e.edge_type = 'IS_SUBTOPIC_OF'
    JOIN graph.nodes o
        ON o.id = e.target_id
        AND o.type = 'ontology'
    WHERE t.type = 'topic';

-- =============================================================================
-- SECTION 5 — COMPILER RUN LOG
--
-- Lightweight audit log for every compile_topic_document execution.
-- Records timing, hash produced, and whether a snapshot was persisted.
-- =============================================================================

CREATE TABLE IF NOT EXISTS cognition.compiler_runs (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_id        TEXT        NOT NULL,
    document_hash   TEXT,                           -- NULL if compilation failed
    snapshot_saved  BOOLEAN     NOT NULL DEFAULT FALSE,
    version_bumped  TEXT,                           -- 'patch' | 'minor' | 'major' | NULL
    duration_ms     INTEGER,
    error           TEXT,                           -- NULL on success
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_compiler_runs_topic
    ON cognition.compiler_runs (topic_id, created_at DESC);

-- =============================================================================
-- END OF COGNITIVE COMPILER SCHEMA
-- =============================================================================
