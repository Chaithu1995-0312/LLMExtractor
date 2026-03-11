#!/usr/bin/env python3
"""
scripts/verify_vector_integrity.py
==================================
Verifies that the vector migration was successful.

Checks:
1. graph.vector_meta has `embedding_v2` column.
2. Count of nodes with `vector_status = 'indexed_v2'`.
3. Count of non-null `embedding_v2` rows.
4. Spot check dimension of `embedding_v2` (must be 1536).
"""

import sys
import os
import logging
import psycopg2
from dotenv import load_dotenv

# Ensure we can import src
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(_REPO_ROOT, ".env"))

DATABASE_URL = os.environ.get("DATABASE_URL")

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("Verifier")

def main():
    if not DATABASE_URL:
        logger.error("DATABASE_URL not set")
        return 1

    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            logger.info("🔍 Checking Schema...")
            cur.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = 'graph' 
                  AND table_name = 'vector_meta' 
                  AND column_name = 'embedding_v2'
            """)
            col = cur.fetchone()
            if not col:
                logger.error("❌ graph.vector_meta.embedding_v2 column MISSING")
                return 1
            logger.info(f"✅ embedding_v2 column exists ({col[1]})")

            logger.info("\n🔍 Checking Node Status...")
            cur.execute("SELECT COUNT(*) FROM graph.nodes WHERE data->>'vector_status' = 'indexed_v2'")
            indexed_count = cur.fetchone()[0]
            logger.info(f"Nodes marked 'indexed_v2': {indexed_count}")

            logger.info("\n🔍 Checking Vector Data...")
            cur.execute("SELECT COUNT(*) FROM graph.vector_meta WHERE embedding_v2 IS NOT NULL")
            vector_count = cur.fetchone()[0]
            logger.info(f"Rows with embedding_v2: {vector_count}")

            if indexed_count != vector_count:
                logger.warning(f"⚠️ Mismatch: {indexed_count} indexed nodes vs {vector_count} vectors")

            logger.info("\n🔍 verifying Dimensions...")
            cur.execute("SELECT vector_dims(embedding_v2) FROM graph.vector_meta WHERE embedding_v2 IS NOT NULL LIMIT 1")
            row = cur.fetchone()
            if row:
                dims = row[0]
                if dims == 1536:
                    logger.info(f"✅ Vector dimension is 1536")
                else:
                    logger.error(f"❌ Vector dimension is {dims} (Expected 1536)")
            else:
                logger.warning("⚠️ No vectors found to verify dimensions")

    except Exception as e:
        logger.error(f"Verification Failed: {e}")
        return 1
    finally:
        conn.close()

    return 0

if __name__ == "__main__":
    sys.exit(main())
