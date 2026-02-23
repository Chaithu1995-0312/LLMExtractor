-- Migration: v2_cognition_upgrade
-- Purpose: Adds support for Budget-Awareness, Calibration, and Enhanced Logging.

-- 1. Budget Tracking
CREATE TABLE IF NOT EXISTS graph.cognition_budget (
    date DATE PRIMARY KEY DEFAULT CURRENT_DATE,
    tokens_used BIGINT DEFAULT 0,
    api_calls INT DEFAULT 0,
    estimated_cost FLOAT DEFAULT 0.0,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 2. Calibration Tracking (Research-Grade)
CREATE TABLE IF NOT EXISTS graph.cognition_calibration (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    log_id UUID REFERENCES graph.cognition_logs(id),
    
    predicted_confidence FLOAT NOT NULL,
    actual_label BOOLEAN, -- NULL until human/system verifies correctness
    
    brier_score FLOAT, -- Computed later: (predicted - actual)^2
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- 3. Enhance Existing Logs
-- Add columns to store granular confidence data and routing info
ALTER TABLE graph.cognition_logs 
ADD COLUMN IF NOT EXISTS confidence_components JSONB, -- Stores {M: 0.8, S: 0.9, E: 0.7, C: 0.8}
ADD COLUMN IF NOT EXISTS threshold_used FLOAT,
ADD COLUMN IF NOT EXISTS escalation_tier INT, -- 1=Local, 2=Flash, 3=Pro
ADD COLUMN IF NOT EXISTS budget_pressure FLOAT; -- Snapshot of pressure (0.0-1.0) at time of call

-- Indexes for Analytics
CREATE INDEX IF NOT EXISTS idx_calibration_log_id ON graph.cognition_calibration(log_id);
