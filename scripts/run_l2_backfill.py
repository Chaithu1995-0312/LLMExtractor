#!/usr/bin/env python3
"""
L2 Semantic Substrate — Backfill Runner (State-Driven)
======================================================
CLI entry point for the embedding backfill job.
Updated to support Cloud Autonomous Pipeline with status tracking.

Usage:
    python scripts/run_l2_backfill.py
    python scripts/run_l2_backfill.py --batch-size 25
    python scripts/run_l2_backfill.py --dry-run
"""

import argparse
import json
import logging
import os
import sys
import psycopg2
import hashlib
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Audit hook (non-breaking — import failure disables hook silently)
# ---------------------------------------------------------------------------
_REPO_ROOT_L2 = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT_L2 not in sys.path:
    sys.path.insert(0, _REPO_ROOT_L2)

try:
    from validation.checks.l2_validator import L2Validator as _L2Validator
    _L2_AUDIT_ENABLED = True
except ImportError:
    _L2Validator = None
    _L2_AUDIT_ENABLED = False

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_SRC_DIR = os.path.join(_REPO_ROOT, "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

try:
    from dotenv import load_dotenv
    _env_path = os.path.join(_REPO_ROOT, ".env")
    if os.path.exists(_env_path):
        load_dotenv(_env_path)
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
def _configure_logging(level_str: str, log_filename: str) -> None:
    level = getattr(logging, level_str.upper(), logging.INFO)
    
    # Clear existing handlers to prevent duplicate output if called multiple times
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        handlers=[
            logging.FileHandler(log_filename),  # Log to file
            logging.StreamHandler(sys.stderr)  # Also log to stderr
        ]
    )

# ---------------------------------------------------------------------------
# OpenAI Helper
# ---------------------------------------------------------------------------
def generate_openai_embedding(text: str, api_key: str):
    """
    Generates embedding using OpenAI API (text-embedding-3-small).
    """
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        )
        return response.data[0].embedding
    except Exception as e:
        logging.error(f"OpenAI Embedding Error: {e}")
        return None

def compute_fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

# ---------------------------------------------------------------------------
# State-Driven Logic
# ---------------------------------------------------------------------------

def run_state_driven_backfill(database_url: str, openai_api_key: str, batch_size: int = 50):
    """
    Processing loop that:
    1. Fetches nodes with status='L1_COMPLETE'
    2. Runs embedding generation
    3. Updates status='L2_COMPLETE'

    Audit hook (non-breaking):
      - L2Validator.validate_brick() is called before each brick is saved.
      - Invalid bricks (empty content, missing id) are logged and skipped.
      - Validation errors never stop the processing loop.
    """
    logger = logging.getLogger("l2_state_runner")

    # ── Open L2 audit validator (non-fatal if unavailable) ──────────────
    l2_validator = None
    if _L2_AUDIT_ENABLED:
        try:
            l2_validator = _L2Validator(batch_id=f"l2-backfill-{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}")
            l2_validator._open_db()
            l2_validator.log("L2_BACKFILL_START", {"batch_size": batch_size})
        except Exception as _ve:
            logger.warning(f"L2 audit validator init failed (non-fatal): {_ve}")
            l2_validator = None

    conn = psycopg2.connect(database_url)
    total_processed = 0
    total_skipped_invalid = 0

    try:
        while True:
            with conn.cursor() as cur:
                # 1. Fetch Candidates
                cur.execute("""
                    SELECT id, data 
                    FROM graph.nodes 
                    WHERE status = 'L1_COMPLETE'
                    LIMIT %s
                    FOR UPDATE SKIP LOCKED
                """, (batch_size,))
                
                rows = cur.fetchall()
                
                if not rows:
                    logger.info("No 'L1_COMPLETE' nodes found. Backfill complete.")
                    break
                
                logger.info(f"Processing batch of {len(rows)} nodes...")
                
                # 2. Process Batch
                for r in rows:
                    node_id = r[0]
                    node_data = r[1]
                    
                    # Mark started
                    cur.execute("UPDATE graph.nodes SET l2_started_at = NOW() WHERE id = %s", (node_id,))
                    
                    try:
                        text = node_data.get("statement") or node_data.get("content")
                        if not text:
                            # Skip empty nodes
                            cur.execute("UPDATE graph.nodes SET status = 'L2_COMPLETE', l2_completed_at = NOW() WHERE id = %s", (node_id,))
                            continue

                        # ── Audit: validate brick before saving ──────────
                        brick_dict = {"id": node_id, "content": text}
                        if l2_validator and not l2_validator.validate_brick(brick_dict):
                            logger.warning(f"[L2Audit] Invalid brick {node_id} — skipping save, marking skipped")
                            total_skipped_invalid += 1
                            # Do NOT save invalid brick; continue to next node
                            # (still mark L2_COMPLETE so it doesn't loop forever)
                            cur.execute("UPDATE graph.nodes SET status = 'L2_COMPLETE', l2_completed_at = NOW() WHERE id = %s", (node_id,))
                            continue

                        # Generate Embedding
                        vector = generate_openai_embedding(text, openai_api_key)
                        
                        if vector:
                            # Update Node Status
                            cur.execute("""
                                UPDATE graph.nodes 
                                SET status = 'L2_COMPLETE', l2_completed_at = NOW()
                                WHERE id = %s
                            """, (node_id,))
                            
                            # Create Sync Brick (Mirror)
                            fingerprint = compute_fingerprint(text)
                            cur.execute("""
                                INSERT INTO sync.bricks (
                                    id, content, state, created_at, status, 
                                    l2_completed_at, fingerprint, 
                                    json_path, start_index, end_index, source_checksum
                                )
                                VALUES (%s, %s, 'FINAL', NOW(), 'L2_COMPLETE', NOW(), %s, %s, %s, %s, %s)
                                ON CONFLICT (id) DO UPDATE SET status = 'L2_COMPLETE', l2_completed_at = NOW()
                            """, (node_id, text, fingerprint, 'N/A', 0, len(text), fingerprint))
                            
                            total_processed += 1
                        else:
                            logger.warning(f"Failed to generate embedding for node {node_id}")
                        
                    except Exception as e:
                        logger.error(f"Failed to process node {node_id}: {e}")
                        # Log to audit trail (non-fatal)
                        if l2_validator:
                            try:
                                l2_validator.log_error("PROCESSING_ERROR", e, {"node_id": node_id})
                            except Exception:
                                pass
                        
            conn.commit()
            
    finally:
        conn.close()
        # ── Close audit validator ────────────────────────────────────────
        if l2_validator:
            try:
                l2_validator.log(
                    "L2_BACKFILL_COMPLETE",
                    {
                        "total_processed": total_processed,
                        "total_skipped_invalid": total_skipped_invalid,
                        **l2_validator.invalid_brick_summary(),
                    },
                    status="ok" if total_skipped_invalid == 0 else "warn",
                )
                l2_validator._close_db()
            except Exception:
                pass

    return total_processed

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    # Ensure logs directory exists
    log_dir = os.path.join(_REPO_ROOT, "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # Create a timestamped log file
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(log_dir, f"l2_backfill_{timestamp}.log")
    
    _configure_logging(args.log_level, log_filename)
    logger = logging.getLogger("l2_main")

    database_url = os.environ.get("DATABASE_URL")
    openai_api_key = os.environ.get("OPENAI_API_KEY")

    if not database_url:
        # Fallback to defaults if env vars missing (local dev)
        database_url = "postgresql://nexus:nexus@localhost:5432/nexus"
    
    if not openai_api_key:
        logger.error("Missing OPENAI_API_KEY")
        return 1

    if args.dry_run:
        conn = psycopg2.connect(database_url)
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM graph.nodes WHERE status = 'L1_COMPLETE'")
            count = cur.fetchone()[0]
        print(f"Dry Run: Found {count} nodes waiting for L2.")
        return 0

    # Execute
    logger.info("Starting State-Driven L2 Backfill...")
    
    processed = run_state_driven_backfill(database_url, openai_api_key, args.batch_size)
    logger.info(f"Completed. Processed {processed} nodes.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
