-- =============================================================================
-- PULSE EVENTS TABLE — L2 Narrator Persistence Layer
-- Stores all GraphManager pulse events for replayable system narrative.
-- This is ADDITIVE ONLY — safe to apply on a live database.
-- =============================================================================

CREATE TABLE IF NOT EXISTS graph.pulse_events (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type  TEXT        NOT NULL,
    node_id     TEXT,                            -- The node this event concerns (nullable for system-level events)
    payload     JSONB,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Composite timeline index — primary query path for /system-story endpoint
CREATE INDEX IF NOT EXISTS idx_pulse_created_at
    ON graph.pulse_events (created_at DESC);

-- Node-scoped index — allows /system-story?node_id=... or topic filtering
CREATE INDEX IF NOT EXISTS idx_pulse_node_id
    ON graph.pulse_events (node_id)
    WHERE node_id IS NOT NULL;

-- Event-type index — allows filtering by event category (NODE_KILLED, NODE_FROZEN, etc.)
CREATE INDEX IF NOT EXISTS idx_pulse_event_type
    ON graph.pulse_events (event_type);
