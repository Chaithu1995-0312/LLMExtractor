#!/usr/bin/env python3
"""
scripts/run_vector_migration.py
===============================
Executes the Critical Data Migration to unified 1536-dim vectors.

This script utilizes the updated L2BackfillEngine to:
1. Scan all nodes with 'loose' or 'forming' lifecycle.
2. Generate text-embedding-3-small (1536) vectors.
3. Write them to graph.vector_meta.embedding_v2.
4. Mark graph.nodes.vector_status as 'indexed_v2'.

Prerequisites:
- OPENAI_API_KEY must be set.
- DATABASE_URL must be set.
- scripts/migrations/001_vector_unification.sql should have been applied (or engine will attempt patch).
"""

import sys
import os
import logging
from dotenv import load_dotenv

# Ensure we can import src
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_SRC_DIR = os.path.join(_REPO_ROOT, "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

# Load env
load_dotenv(os.path.join(_REPO_ROOT, ".env"))

from nexus.vector.l2_backfill import L2BackfillEngine

def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    )

def main():
    configure_logging()
    logger = logging.getLogger("VectorMigration")
    
    logger.info("🚀 Starting Vector Unification Migration (v1 -> v2)")
    logger.info("Target: text-embedding-3-small (1536 dims)")

    try:
        engine = L2BackfillEngine()
        
        # Run with a slightly higher batch size for migration speed, if API limits allow
        summary = engine.run(batch_size=50)
        
        logger.info("--------------------------------------------------")
        logger.info("Migration Summary:")
        logger.info(f"  Nodes Scanned:    {summary.total_nodes_scanned}")
        logger.info(f"  Vectors Created:  {summary.total_embeddings_created}")
        logger.info(f"  Failures:         {summary.failures}")
        logger.info(f"  Lifecycle Skips:  {summary.skipped_lifecycle_guard}")
        logger.info(f"  Duration:         {summary.duration_seconds:.2f}s")
        logger.info("--------------------------------------------------")
        
        if summary.failures > 0:
            logger.warning("⚠️ Some nodes failed. Re-run this script to retry.")
            sys.exit(1)
            
        logger.info("✅ Migration Complete. All eligible nodes are indexed_v2.")
        
    except Exception as e:
        logger.critical(f"Migration Failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
