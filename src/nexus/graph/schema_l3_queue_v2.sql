-- L3 Task Queue Hardening
-- Adds heartbeat and constraints for better atomicity and safety

ALTER TABLE graph.l3_tasks 
ADD COLUMN IF NOT EXISTS last_heartbeat TIMESTAMP WITH TIME ZONE NULL;

-- Ensure valid status
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'valid_status') THEN
        ALTER TABLE graph.l3_tasks 
        ADD CONSTRAINT valid_status 
        CHECK (status IN ('pending', 'running', 'completed', 'failed'));
    END IF;
END $$;

-- Optional: Unique index for pending tasks to prevent duplicate scheduling
-- CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_scheduled_task
-- ON graph.l3_tasks (task_type, payload)
-- WHERE status = 'pending';
