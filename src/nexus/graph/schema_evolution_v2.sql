-- =============================================================================
-- EVOLUTION V2 — Three-Layer Intelligence Architecture
-- Applied once against Postgres. All statements are idempotent.
--
-- Adds:
--   1. Archival infrastructure to graph.nodes + graph.edges
--   2. Concept version timeline table
--   3. graph_ai schema for AI Advisory layer
--   4. graph_sandbox schema for Autonomous Sandbox
--   5. Real-time metrics materialized views
--   6. Extended edge types for semantic graph
-- =============================================================================

-- =============================================================================
-- SECTION 1 — ARCHIVAL INFRASTRUCTURE (graph.nodes + graph.edges)
-- =============================================================================

-- Add archival columns to graph.nodes
ALTER TABLE graph.nodes
    ADD COLUMN IF NOT EXISTS archived           BOOLEAN     NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS concept_version    INTEGER     NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS archived_at        TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS cluster_id         TEXT,
    ADD COLUMN IF NOT EXISTS branch_id          TEXT,
    ADD COLUMN IF NOT EXISTS author_id          TEXT        NOT NULL DEFAULT 'system',
    ADD COLUMN IF NOT EXISTS stability_score    FLOAT       NOT NULL DEFAULT 1.0;

-- Add archival columns to graph.edges
ALTER TABLE graph.edges
    ADD COLUMN IF NOT EXISTS archived           BOOLEAN     NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS archived_at        TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS author_id          TEXT        NOT NULL DEFAULT 'system',
    ADD COLUMN IF NOT EXISTS similarity_score   FLOAT;

-- Indexes for archival queries
CREATE INDEX IF NOT EXISTS idx_nodes_archived
    ON graph.nodes (archived)
    WHERE archived = FALSE;

CREATE INDEX IF NOT EXISTS idx_nodes_cluster
    ON graph.nodes (cluster_id)
    WHERE cluster_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_nodes_author
    ON graph.nodes (author_id);

CREATE INDEX IF NOT EXISTS idx_edges_archived
    ON graph.edges (archived)
    WHERE archived = FALSE;

CREATE INDEX IF NOT EXISTS idx_edges_edge_type_active
    ON graph.edges (edge_type)
    WHERE archived = FALSE;

-- =============================================================================
-- SECTION 2 — CONCEPT VERSION TIMELINE TABLE
--
-- One row per promotion event. Each time a concept chain is replaced or
-- branched, we record the transition here. This is the historical anchor.
-- =============================================================================

CREATE TABLE IF NOT EXISTS graph.concept_versions (
    concept_id          TEXT            NOT NULL,
    version_number      INTEGER         NOT NULL,
    root_node_id        TEXT            NOT NULL,
    previous_root_id    TEXT,                       -- NULL for v1

    change_reason       TEXT,
    change_type         TEXT            NOT NULL DEFAULT 'REPLACE',
                                                    -- REPLACE | BRANCH | MERGE | FORK
    promoted_from       TEXT,                       -- 'sandbox' | 'manual' | 'ai_advisory'
    promoted_by         TEXT            NOT NULL DEFAULT 'system',

    archived_chain      JSONB           NOT NULL DEFAULT '[]',
                                                    -- snapshot of node_ids archived during this promotion
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    PRIMARY KEY (concept_id, version_number)
);

CREATE INDEX IF NOT EXISTS idx_concept_versions_concept
    ON graph.concept_versions (concept_id);

CREATE INDEX IF NOT EXISTS idx_concept_versions_created
    ON graph.concept_versions (created_at DESC);

-- =============================================================================
-- SECTION 3 — AI ADVISORY SCHEMA
--
-- AI can suggest, but never mutate Core directly.
-- All suggestions require human approval.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS graph_ai;

CREATE TABLE IF NOT EXISTS graph_ai.suggestions (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),

    suggestion_type     TEXT            NOT NULL,
                                                    -- MERGE | CONSOLIDATE | ADJUST_THRESHOLD
                                                    -- FLAG_UNSTABLE | FLAG_CONFLICT | SUMMARIZE
    source_nodes        TEXT[]          NOT NULL DEFAULT '{}',
    target_nodes        TEXT[]          NOT NULL DEFAULT '{}',

    reasoning           TEXT,
    confidence          FLOAT           NOT NULL DEFAULT 0.0,

    -- Periodically-generated advisory context
    analysis_run_id     UUID,
    analysis_period     TEXT,                       -- 'hourly' | 'nightly' | 'weekly'

    status              TEXT            NOT NULL DEFAULT 'pending'
                                        CHECK (status IN ('pending', 'approved', 'rejected', 'expired')),

    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    reviewed_at         TIMESTAMPTZ,
    reviewed_by         TEXT,
    review_notes        TEXT
);

CREATE INDEX IF NOT EXISTS idx_ai_suggestions_status
    ON graph_ai.suggestions (status);

CREATE INDEX IF NOT EXISTS idx_ai_suggestions_type
    ON graph_ai.suggestions (suggestion_type);

CREATE INDEX IF NOT EXISTS idx_ai_suggestions_created
    ON graph_ai.suggestions (created_at DESC);

-- Advisory run history: tracks each periodic AI analysis job
CREATE TABLE IF NOT EXISTS graph_ai.analysis_runs (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    period              TEXT            NOT NULL,   -- 'hourly' | 'nightly'
    started_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMPTZ,
    suggestions_created INTEGER         NOT NULL DEFAULT 0,
    status              TEXT            NOT NULL DEFAULT 'running'
                                        CHECK (status IN ('running', 'completed', 'failed')),
    error               TEXT
);

-- =============================================================================
-- SECTION 4 — SANDBOX SCHEMA
--
-- Isolated evolution space. AI can freely mutate. Never touches Core directly.
-- Promotion requires an explicit human approval workflow.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS graph_sandbox;

CREATE TABLE IF NOT EXISTS graph_sandbox.nodes (
    id                  TEXT            PRIMARY KEY,
    type                TEXT            NOT NULL,
    data                JSONB           NOT NULL DEFAULT '{}',
    original_node_id    TEXT,                       -- pointer back to Core node (if copied)
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    modified_at         TIMESTAMPTZ,
    sandbox_run_id      UUID            NOT NULL
);

CREATE TABLE IF NOT EXISTS graph_sandbox.edges (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id           TEXT            NOT NULL REFERENCES graph_sandbox.nodes(id) ON DELETE CASCADE,
    target_id           TEXT            NOT NULL REFERENCES graph_sandbox.nodes(id) ON DELETE CASCADE,
    edge_type           TEXT            NOT NULL,
    metadata            JSONB           NOT NULL DEFAULT '{}',
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    sandbox_run_id      UUID            NOT NULL,
    UNIQUE (source_id, target_id, edge_type, sandbox_run_id)
);

-- Sandbox run metadata: tracks each on-demand simulation session
CREATE TABLE IF NOT EXISTS graph_sandbox.runs (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    initiated_by        TEXT            NOT NULL DEFAULT 'system',
    concept_ids         TEXT[]          NOT NULL DEFAULT '{}',    -- concept roots copied into sandbox
    node_count          INTEGER         NOT NULL DEFAULT 0,
    edge_count          INTEGER         NOT NULL DEFAULT 0,
    status              TEXT            NOT NULL DEFAULT 'running'
                                        CHECK (status IN ('running', 'completed', 'promoted', 'discarded')),
    diff_summary        JSONB           NOT NULL DEFAULT '{}',
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMPTZ
);

-- Promotion conflict tracking: when sandbox → Core has conflicts
CREATE TABLE IF NOT EXISTS graph_sandbox.promotions (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id              UUID            NOT NULL REFERENCES graph_sandbox.runs(id),
    conflict_severity   TEXT            NOT NULL DEFAULT 'NONE'
                                        CHECK (conflict_severity IN ('NONE', 'LOW', 'MEDIUM', 'HIGH')),
    conflict_details    JSONB           NOT NULL DEFAULT '{}',
    resolution_strategy TEXT            NOT NULL DEFAULT 'PENDING'
                                        CHECK (resolution_strategy IN ('PENDING', 'REPLACE', 'BRANCH', 'NEW_CONCEPT', 'MANUAL')),
    resolution_applied  BOOLEAN         NOT NULL DEFAULT FALSE,
    resolved_by         TEXT,
    resolved_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sandbox_runs_status
    ON graph_sandbox.runs (status);

CREATE INDEX IF NOT EXISTS idx_sandbox_promotions_pending
    ON graph_sandbox.promotions (resolution_applied)
    WHERE resolution_applied = FALSE;

-- =============================================================================
-- SECTION 5 — REAL-TIME METRICS MATERIALIZED VIEWS
--
-- Deterministic analytics. No LLM required.
-- Refresh on schedule (nightly or after major drift runs).
-- =============================================================================

-- View 1: Active concept roots (no incoming superseded_by on active nodes)
CREATE MATERIALIZED VIEW IF NOT EXISTS graph.mv_concept_roots AS
    SELECT n.id AS concept_id,
           n.data->>'statement' AS statement,
           n.created_at,
           n.cluster_id,
           n.author_id,
           n.stability_score
    FROM graph.nodes n
    LEFT JOIN graph.edges e
        ON n.id = e.target_id
        AND e.edge_type = 'superseded_by'
        AND e.archived = FALSE
    WHERE e.id IS NULL
      AND n.archived = FALSE
WITH DATA;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_concept_roots_id
    ON graph.mv_concept_roots (concept_id);

-- View 2: Cluster health — instability per cluster
CREATE MATERIALIZED VIEW IF NOT EXISTS graph.mv_cluster_health AS
    SELECT
        n.cluster_id,
        COUNT(DISTINCT n.id)                                            AS node_count,
        COUNT(DISTINCT e.id) FILTER (WHERE e.edge_type = 'superseded_by')   AS supersession_count,
        COUNT(DISTINCT e.id) FILTER (WHERE e.edge_type = 'refines')         AS refinement_count,
        COUNT(DISTINCT e.id) FILTER (WHERE e.edge_type = 'contradicts')     AS conflict_count,
        CASE
            WHEN COUNT(DISTINCT n.id) = 0 THEN 0.0
            ELSE ROUND((COUNT(DISTINCT e.id) FILTER (WHERE e.edge_type = 'superseded_by')::NUMERIC
                        / NULLIF(COUNT(DISTINCT n.id), 0)), 4)
        END                                                             AS instability_score,
        MAX(e.created_at)                                               AS last_activity_at
    FROM graph.nodes n
    LEFT JOIN graph.edges e
        ON n.id = e.source_id
        AND e.archived = FALSE
    WHERE n.archived = FALSE
      AND n.cluster_id IS NOT NULL
    GROUP BY n.cluster_id
WITH DATA;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_cluster_health_id
    ON graph.mv_cluster_health (cluster_id);

-- View 3: Supersession velocity — daily edge creation rate
CREATE MATERIALIZED VIEW IF NOT EXISTS graph.mv_supersession_velocity AS
    SELECT
        DATE_TRUNC('day', created_at)::DATE     AS day,
        COUNT(*)                                AS supersession_count,
        COUNT(*) FILTER (WHERE archived = FALSE) AS active_count
    FROM graph.edges
    WHERE edge_type = 'superseded_by'
    GROUP BY DATE_TRUNC('day', created_at)::DATE
    ORDER BY day DESC
WITH DATA;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_supersession_velocity_day
    ON graph.mv_supersession_velocity (day);

-- View 4: Convergence index — average similarity per week (refinement edges)
CREATE MATERIALIZED VIEW IF NOT EXISTS graph.mv_convergence_index AS
    SELECT
        DATE_TRUNC('week', created_at)::DATE    AS week,
        COUNT(*)                                AS refinement_count,
        ROUND(AVG((metadata->>'similarity_score')::FLOAT)::NUMERIC, 4) AS avg_similarity,
        ROUND(STDDEV((metadata->>'similarity_score')::FLOAT)::NUMERIC, 4) AS similarity_stddev
    FROM graph.edges
    WHERE edge_type = 'refines'
      AND metadata->>'similarity_score' IS NOT NULL
      AND archived = FALSE
    GROUP BY DATE_TRUNC('week', created_at)::DATE
    ORDER BY week DESC
WITH DATA;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_convergence_week
    ON graph.mv_convergence_index (week);

-- =============================================================================
-- SECTION 6 — STABILITY SCORE FUNCTION
--
-- Deterministic formula: stability = 1 / (1 + supersession_count)
-- Stored in graph.nodes.stability_score on each drift run.
-- =============================================================================

CREATE OR REPLACE FUNCTION graph.compute_stability_score(p_node_id TEXT)
RETURNS FLOAT AS $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT COUNT(*)
    INTO v_count
    FROM graph.edges
    WHERE source_id = p_node_id
      AND edge_type = 'superseded_by'
      AND archived = FALSE;

    RETURN 1.0 / (1.0 + v_count);
END;
$$ LANGUAGE plpgsql STABLE;

-- =============================================================================
-- SECTION 7 — REFRESH HELPER
--
-- Call this after bulk drift runs to keep views current.
-- =============================================================================

CREATE OR REPLACE FUNCTION graph.refresh_metrics()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY graph.mv_concept_roots;
    REFRESH MATERIALIZED VIEW CONCURRENTLY graph.mv_cluster_health;
    REFRESH MATERIALIZED VIEW CONCURRENTLY graph.mv_supersession_velocity;
    REFRESH MATERIALIZED VIEW CONCURRENTLY graph.mv_convergence_index;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- END OF EVOLUTION V2 SCHEMA
-- =============================================================================
