"""
apply_evolution_schema.py — Apply Evolution V2 Schema Migration
===============================================================
Run once against Postgres to install:
  - Archival columns on graph.nodes + graph.edges
  - graph.concept_versions table
  - graph_ai schema + tables
  - graph_sandbox schema + tables
  - Materialized views (mv_concept_roots, mv_cluster_health, etc.)
  - SQL helper functions (compute_stability_score, refresh_metrics)

Usage:
    python scripts/apply_evolution_schema.py
    python scripts/apply_evolution_schema.py --dry-run   # print SQL only
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from nexus.db import get_adapter

SCHEMA_FILE = os.path.join(
    os.path.dirname(__file__), "..", "src", "nexus", "graph", "schema_evolution_v2.sql"
)


def load_sql(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def split_statements(sql: str):
    """
    Split SQL into individual statements for sequential execution.
    Handles dollar-quoted functions ($$...$$) correctly.
    """
    statements = []
    current = []
    in_dollar_quote = False

    for line in sql.splitlines():
        stripped = line.strip()

        # Toggle dollar-quote block tracking
        if "$$" in line:
            count = line.count("$$")
            if count % 2 != 0:
                in_dollar_quote = not in_dollar_quote

        current.append(line)

        # Only split on semicolons outside dollar-quote blocks
        if not in_dollar_quote and stripped.endswith(";"):
            stmt = "\n".join(current).strip()
            if stmt and not stmt.startswith("--"):
                statements.append(stmt)
            current = []

    # Catch any trailing statement without semicolon
    remainder = "\n".join(current).strip()
    if remainder and not remainder.startswith("--"):
        statements.append(remainder)

    return [s for s in statements if s]


def apply_schema(dry_run: bool = False):
    print("=" * 60)
    print("Evolution V2 Schema Migration")
    print("=" * 60)

    sql = load_sql(SCHEMA_FILE)
    statements = split_statements(sql)

    print(f"\nLoaded {len(statements)} SQL statements from schema_evolution_v2.sql\n")

    if dry_run:
        print("--- DRY RUN (no changes applied) ---\n")
        for i, stmt in enumerate(statements, 1):
            preview = stmt[:120].replace("\n", " ")
            print(f"  [{i:03d}] {preview}...")
        print("\nDry run complete.")
        return

    db = get_adapter()
    success = 0
    skipped = 0
    failed = 0

    for i, stmt in enumerate(statements, 1):
        preview = stmt[:80].replace("\n", " ")
        try:
            db.execute(stmt)
            print(f"  [OK ] [{i:03d}] {preview}")
            success += 1
        except Exception as exc:
            err = str(exc).strip()
            # Idempotency: many statements use IF NOT EXISTS / ON CONFLICT
            # but some errors (like "already exists") are safe to skip.
            safe_errors = [
                "already exists",
                "duplicate column",
                "does not exist",   # For CONCURRENTLY refresh on empty view
            ]
            if any(s in err.lower() for s in safe_errors):
                print(f"  [SKP] [{i:03d}] {preview} (skipped: {err[:60]})")
                skipped += 1
            else:
                print(f"  [ERR] [{i:03d}] {preview}")
                print(f"         Error: {err[:200]}")
                failed += 1

    print("\n" + "=" * 60)
    print(f"Migration complete: {success} ok, {skipped} skipped, {failed} failed")
    print("=" * 60)

    if failed > 0:
        print("\n⚠  Some statements failed. Review errors above.")
        sys.exit(1)
    else:
        print("\n✅ Evolution V2 schema applied successfully.")
        print("\nNext steps:")
        print("  1. Run scripts/test_evolution_api.py to verify")
        print("  2. Start a drift run to populate vectors")
        print("  3. Call graph.refresh_metrics() after the first drift run")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply Evolution V2 Schema")
    parser.add_argument("--dry-run", action="store_true", help="Print statements without executing")
    args = parser.parse_args()
    apply_schema(dry_run=args.dry_run)
