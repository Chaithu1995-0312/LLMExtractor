#!/usr/bin/env python3
"""
Migration: 20240628_audit_tables
=================================
Creates the audit schema and processing_trail / alerts tables.
Idempotent — safe to run multiple times.

Usage:
    python scripts/migrations/20240628_audit_tables.py
"""

import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_SRC_DIR = os.path.join(_REPO_ROOT, "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_REPO_ROOT, ".env"))
except ImportError:
    pass

import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://nexus:nexus@localhost:5432/nexus")

DDL = """
-- -------------------------------------------------------------------------
-- Audit schema
-- -------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS audit;

-- -------------------------------------------------------------------------
-- audit.processing_trail
-- Per-stage processing event log. Lightweight append-only.
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit.processing_trail (
    id              SERIAL PRIMARY KEY,
    batch_id        VARCHAR(64)  NOT NULL,
    stage           VARCHAR(4)   CHECK (stage IN ('PRE', 'L1', 'L2', 'L3', 'POST')),
    event_type      VARCHAR(40)  NOT NULL,
    status          VARCHAR(20)  DEFAULT 'ok',
    latency_ms      INTEGER,                        -- processing time in ms
    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    metadata        JSONB
);

CREATE INDEX IF NOT EXISTS idx_trail_batch_id  ON audit.processing_trail (batch_id);
CREATE INDEX IF NOT EXISTS idx_trail_stage     ON audit.processing_trail (stage);
CREATE INDEX IF NOT EXISTS idx_trail_created   ON audit.processing_trail (created_at DESC);

-- -------------------------------------------------------------------------
-- audit.alerts
-- High-severity events flagged for operator attention.
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit.alerts (
    id              SERIAL PRIMARY KEY,
    trail_id        INTEGER REFERENCES audit.processing_trail(id) ON DELETE CASCADE,
    severity        VARCHAR(10)  DEFAULT 'HIGH' CHECK (severity IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    acknowledged    BOOLEAN      DEFAULT FALSE,
    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    notes           TEXT
);

CREATE INDEX IF NOT EXISTS idx_alerts_unack ON audit.alerts (acknowledged) WHERE acknowledged = FALSE;
"""


def upgrade():
    print(f"[migration] Connecting to: {DATABASE_URL.split('@')[-1]}")
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(DDL)
        print("[migration] ✅  audit.processing_trail and audit.alerts created (idempotent).")
    except Exception as e:
        print(f"[migration] ❌  Failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    upgrade()
