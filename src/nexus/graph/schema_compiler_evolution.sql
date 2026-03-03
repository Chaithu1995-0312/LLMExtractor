-- Schema Evolution for TCC
-- Add root_topic flag to nodes
-- The 'data' column in graph.nodes is JSONB in Postgres, we can add it there, 
-- but a dedicated column might be faster for root topic identification if needed.
-- Requirement says: Add "root_topic": boolean to Node schema.

-- Adding column to graph.nodes
ALTER TABLE graph.nodes ADD COLUMN IF NOT EXISTS root_topic BOOLEAN DEFAULT FALSE;

-- Extend bricks to include lifecycle. 
-- The bricks table already has a 'state' column which maps to lifecycle.
-- IMPROVISE -> Loose
-- FORMING -> Forming
-- FINAL -> Frozen
-- SUPERSEDED -> Killed
-- The requirement explicitly asks to add "lifecycle": "Loose | Forming | Frozen | Killed"
-- We will add it as a new column or ensure 'state' is compatible.
-- To be safe and meet the requirement literally:
ALTER TABLE sync.bricks ADD COLUMN IF NOT EXISTS lifecycle TEXT CHECK (lifecycle IN ('Loose', 'Forming', 'Frozen', 'Killed')) DEFAULT 'Loose';

-- Update existing bricks based on state
UPDATE sync.bricks SET lifecycle = 'Loose' WHERE state = 'IMPROVISE' AND lifecycle IS NULL;
UPDATE sync.bricks SET lifecycle = 'Forming' WHERE state = 'FORMING' AND lifecycle IS NULL;
UPDATE sync.bricks SET lifecycle = 'Frozen' WHERE state = 'FINAL' AND lifecycle IS NULL;
UPDATE sync.bricks SET lifecycle = 'Killed' WHERE state = 'SUPERSEDED' AND lifecycle IS NULL;
