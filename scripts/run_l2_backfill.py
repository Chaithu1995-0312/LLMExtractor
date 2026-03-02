#!/usr/bin/env python3
"""
L2 Semantic Substrate — Backfill Runner
========================================
CLI entry point for the embedding backfill job.

Usage:
    python scripts/run_l2_backfill.py
    python scripts/run_l2_backfill.py --batch-size 25
    python scripts/run_l2_backfill.py --dry-run
    python scripts/run_l2_backfill.py --log-level DEBUG

Exits with code 0 if failures == 0, else code 1.
Prints the summary JSON to stdout regardless of exit code so CI/CD
pipelines can capture it even on partial failure.
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Path bootstrap — ensure 'src/' is on sys.path so nexus imports resolve
# when running from repo root.
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_SRC_DIR = os.path.join(_REPO_ROOT, "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

# ---------------------------------------------------------------------------
# Load .env if dotenv is available (non-fatal if not installed)
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(_REPO_ROOT, ".env")
    if os.path.exists(_env_path):
        load_dotenv(_env_path)
        # Loaded silently — logger not yet configured at this point
except ImportError:
    pass  # python-dotenv not installed; rely on environment variables being pre-set


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="L2 Semantic Substrate — OpenAI embedding backfill for graph.nodes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Standard run with default batch size of 50
  python scripts/run_l2_backfill.py

  # Smaller batches (useful for debugging or slow API)
  python scripts/run_l2_backfill.py --batch-size 10

  # Dry run: count eligible nodes without calling API or writing DB
  python scripts/run_l2_backfill.py --dry-run

  # Verbose logging
  python scripts/run_l2_backfill.py --log-level DEBUG
        """,
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        metavar="N",
        help="Number of nodes to process per batch (default: 50)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count eligible nodes and print estimate without calling API or writing to DB.",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def _configure_logging(level_str: str) -> None:
    level = getattr(logging, level_str.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stderr,   # Structured logs → stderr; JSON summary → stdout
    )


# ---------------------------------------------------------------------------
# Dry-run helper
# ---------------------------------------------------------------------------

def _dry_run(database_url: str) -> None:
    """
    Counts eligible nodes without touching the API or writing to DB.
    Prints a human-readable pre-flight report.
    """
    import psycopg2

    ELIGIBLE_LIFECYCLES = ("loose", "forming")

    _SQL_COUNT = """
        SELECT COUNT(*)
        FROM graph.nodes
        WHERE data->>'lifecycle' = ANY(%s)
        AND   (data->>'vector_status' IS NULL OR data->>'vector_status' != 'indexed')
    """
    _SQL_BREAKDOWN = """
        SELECT data->>'lifecycle' AS lifecycle, COUNT(*) AS cnt
        FROM graph.nodes
        WHERE data->>'lifecycle' = ANY(%s)
        AND   (data->>'vector_status' IS NULL OR data->>'vector_status' != 'indexed')
        GROUP BY 1
        ORDER BY 1
    """
    _SQL_ALREADY_INDEXED = """
        SELECT COUNT(*)
        FROM graph.nodes
        WHERE data->>'vector_status' = 'indexed'
    """
    _SQL_TOTAL = """
        SELECT COUNT(*) FROM graph.nodes
    """

    conn = psycopg2.connect(database_url)
    try:
        with conn.cursor() as cur:
            cur.execute(_SQL_COUNT, (list(ELIGIBLE_LIFECYCLES),))
            eligible = cur.fetchone()[0]

            cur.execute(_SQL_BREAKDOWN, (list(ELIGIBLE_LIFECYCLES),))
            breakdown = cur.fetchall()

            cur.execute(_SQL_ALREADY_INDEXED)
            already_indexed = cur.fetchone()[0]

            cur.execute(_SQL_TOTAL)
            total = cur.fetchone()[0]
    finally:
        conn.close()

    print("\n" + "=" * 60)
    print("  L2 BACKFILL — DRY RUN REPORT")
    print("=" * 60)
    print(f"  Total nodes in graph.nodes : {total}")
    print(f"  Already indexed            : {already_indexed}")
    print(f"  Eligible (will be embedded): {eligible}")
    print()
    print("  Lifecycle breakdown of eligible nodes:")
    for row in breakdown:
        print(f"    {row[0]:<20}  {row[1]:>6}")
    print()
    print(f"  Estimated API calls        : {eligible}")
    print(f"  Estimated cost (approx)    : ${eligible * 0.00002:.4f}  "
          f"(text-embedding-3-small @ $0.02 / 1M tokens, ~1 token/node avg)")
    print("=" * 60)
    print("  Run without --dry-run to execute.\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    args = _parse_args()
    _configure_logging(args.log_level)

    logger = logging.getLogger("l2_backfill_runner")
    logger.info("=" * 60)
    logger.info("  L2 Semantic Substrate — Embedding Backfill")
    logger.info("  Started at: %s", datetime.now(timezone.utc).isoformat())
    logger.info("=" * 60)

    # Validate environment before importing the engine
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL is not set. Cannot connect to PostgreSQL.")
        print(json.dumps({
            "error": "DATABASE_URL not set",
            "total_nodes_scanned": 0,
            "total_embeddings_created": 0,
            "failures": 0,
            "duration_seconds": 0.0,
        }))
        return 1

    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key and not args.dry_run:
        logger.error("OPENAI_API_KEY is not set. Cannot call embedding API.")
        print(json.dumps({
            "error": "OPENAI_API_KEY not set",
            "total_nodes_scanned": 0,
            "total_embeddings_created": 0,
            "failures": 0,
            "duration_seconds": 0.0,
        }))
        return 1

    # ----------------------------------------------------------------
    # Dry-run path
    # ----------------------------------------------------------------
    if args.dry_run:
        logger.info("Dry-run mode activated. No API calls or DB writes will be made.")
        try:
            _dry_run(database_url)
        except Exception as exc:
            logger.error("Dry-run failed: %s", exc, exc_info=True)
            return 1
        return 0

    # ----------------------------------------------------------------
    # Live run
    # ----------------------------------------------------------------
    logger.info("Batch size: %d", args.batch_size)

    try:
        from nexus.vector.l2_backfill import L2BackfillEngine
    except ImportError as exc:
        logger.error("Failed to import L2BackfillEngine: %s", exc, exc_info=True)
        print(json.dumps({
            "error": f"Import failed: {exc}",
            "total_nodes_scanned": 0,
            "total_embeddings_created": 0,
            "failures": 0,
            "duration_seconds": 0.0,
        }))
        return 1

    try:
        engine = L2BackfillEngine(
            database_url=database_url,
            openai_api_key=openai_api_key,
        )
        summary = engine.run(batch_size=args.batch_size)
    except Exception as exc:
        logger.error("Backfill engine raised an unhandled exception: %s", exc, exc_info=True)
        print(json.dumps({
            "error": str(exc),
            "total_nodes_scanned": 0,
            "total_embeddings_created": 0,
            "failures": 1,
            "duration_seconds": 0.0,
        }))
        return 1

    # ----------------------------------------------------------------
    # Output summary JSON to stdout
    # ----------------------------------------------------------------
    summary_dict = summary.to_dict()
    summary_dict["completed_at"] = datetime.now(timezone.utc).isoformat()
    summary_dict["model"] = "text-embedding-3-small"
    summary_dict["embedding_version"] = "v1"
    summary_dict["batch_size_used"] = args.batch_size

    print(json.dumps(summary_dict, indent=2))

    # ----------------------------------------------------------------
    # Exit code: 0 = fully clean, 1 = partial failures
    # ----------------------------------------------------------------
    if summary.failures > 0:
        logger.warning(
            "%d node(s) failed to embed. Re-run to retry — they remain 'pending'.",
            summary.failures,
        )
        return 1

    logger.info("Backfill completed with zero failures. ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
