"""
Apply the Cognitive Compiler schema to the Postgres database.
Idempotent — safe to run multiple times.

Usage:
    python scripts/apply_cognitive_compiler_schema.py
"""
import os
import sys

# Resolve repo root so we can import nexus packages from src/
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(repo_root, "src"))

from nexus.db import get_adapter

SQL_FILE = os.path.join(repo_root, "src", "nexus", "graph", "schema_cognitive_compiler.sql")


def apply():
    print("[apply_cognitive_compiler_schema] Starting …")
    db = get_adapter()

    # 1. Ensure the 'cognition' schema exists BEFORE running the SQL file
    #    (the SQL file itself does not CREATE SCHEMA to stay minimal).
    db.execute("CREATE SCHEMA IF NOT EXISTS cognition")
    print("[apply_cognitive_compiler_schema] Schema 'cognition' ensured.")

    # 2. Read and execute the SQL file statement-by-statement.
    #    psycopg2 cursors can execute multi-statement strings, but splitting
    #    on semicolons is safer for comment-heavy DDL.
    with open(SQL_FILE, "r", encoding="utf-8") as fh:
        raw = fh.read()

    # Split on semicolons but ignore empty/whitespace-only segments.
    statements = [s.strip() for s in raw.split(";") if s.strip()]

    ok = 0
    failed = 0
    for stmt in statements:
        # Skip pure comment blocks
        lines = [l for l in stmt.splitlines() if not l.strip().startswith("--")]
        clean = "\n".join(lines).strip()
        if not clean:
            continue
        try:
            db.execute(stmt)
            ok += 1
        except Exception as e:
            print(f"[WARN] Statement failed (non-fatal for IF NOT EXISTS DDL): {e}")
            failed += 1

    print(
        f"[apply_cognitive_compiler_schema] Done. "
        f"{ok} statements OK, {failed} skipped/failed."
    )


if __name__ == "__main__":
    apply()
