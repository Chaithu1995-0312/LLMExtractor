-- =============================================================================
-- Migration: 20240629_audit_triggers
-- Anomaly detection trigger on audit.processing_trail
-- Idempotent — safe to run multiple times.
--
-- Apply via:
--   psql $DATABASE_URL -f scripts/migrations/20240629_audit_triggers.sql
-- =============================================================================

-- Drop if re-running (idempotent)
DROP TRIGGER IF EXISTS anomaly_detection ON audit.processing_trail;
DROP FUNCTION IF EXISTS audit.alert_anomaly();

-- -------------------------------------------------------------------------
-- Function: audit.alert_anomaly()
-- Inserts a HIGH-severity alert whenever a validation failure or processing
-- error is recorded in audit.processing_trail.
-- -------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION audit.alert_anomaly()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.event_type IN (
        'VALIDATION_FAIL',
        'PROCESSING_ERROR',
        'L1_FAILURE',
        'L2_FAILURE',
        'L3_FAILURE',
        'SPLIT_FAILURE',
        'INVALID_MESSAGE'
    ) THEN
        INSERT INTO audit.alerts (trail_id, severity, acknowledged, notes)
        VALUES (
            NEW.id,
            'HIGH',
            FALSE,
            format('Auto-flagged: event_type=%s batch_id=%s', NEW.event_type, NEW.batch_id)
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- -------------------------------------------------------------------------
-- Trigger: anomaly_detection
-- Fires AFTER each INSERT on audit.processing_trail.
-- -------------------------------------------------------------------------
CREATE TRIGGER anomaly_detection
AFTER INSERT ON audit.processing_trail
FOR EACH ROW EXECUTE FUNCTION audit.alert_anomaly();
