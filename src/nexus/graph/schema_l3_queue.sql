-- L3 Task Queue for Transactional Orchestration
-- Replaces Redis/Celery broker

CREATE TABLE IF NOT EXISTS graph.l3_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', -- pending, running, completed, failed
    attempts INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    scheduled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    locked_at TIMESTAMP WITH TIME ZONE NULL,
    completed_at TIMESTAMP WITH TIME ZONE NULL,
    error TEXT NULL,
    traceback TEXT NULL,
    worker_id TEXT NULL
);

-- Index for efficient queue polling
CREATE INDEX IF NOT EXISTS idx_l3_tasks_polling ON graph.l3_tasks (status, scheduled_at) 
WHERE status = 'pending';

-- Index for visibility timeout cleanup
CREATE INDEX IF NOT EXISTS idx_l3_tasks_timeout ON graph.l3_tasks (status, locked_at) 
WHERE status = 'running';
