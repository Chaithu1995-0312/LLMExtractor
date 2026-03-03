-- Migration: Add granular status tracking and timestamps for Cloud Automation Pipeline
-- Applies to graph.nodes and sync.bricks

-- 1. Create the status enum if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'cognitive_status') THEN
        CREATE TYPE cognitive_status AS ENUM (
            'L1_PENDING', 
            'L1_COMPLETE', 
            'L2_PENDING', 
            'L2_COMPLETE', 
            'L3_PENDING', 
            'L3_COMPLETE'
        );
    END IF;
END $$;

-- 2. Add columns to graph.nodes
ALTER TABLE graph.nodes 
ADD COLUMN IF NOT EXISTS status cognitive_status DEFAULT 'L1_PENDING',
ADD COLUMN IF NOT EXISTS l1_started_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS l1_completed_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS l2_started_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS l2_completed_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS l3_started_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS l3_completed_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS last_processed_at TIMESTAMPTZ DEFAULT NOW();

-- 3. Add columns to sync.bricks
ALTER TABLE sync.bricks 
ADD COLUMN IF NOT EXISTS status cognitive_status DEFAULT 'L2_PENDING',
ADD COLUMN IF NOT EXISTS l2_started_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS l2_completed_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS l3_started_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS l3_completed_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS last_processed_at TIMESTAMPTZ DEFAULT NOW();

-- 4. Index for performance during periodic state-checks
CREATE INDEX IF NOT EXISTS idx_nodes_status ON graph.nodes(status);
CREATE INDEX IF NOT EXISTS idx_bricks_status ON sync.bricks(status);
