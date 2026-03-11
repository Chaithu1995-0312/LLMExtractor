"""
validation/checks/l3_validator.py
==================================
L3 Clustering Audit — validates topic hierarchy and checks for orphaned bricks.

Checks:
  1. Orphaned bricks: L2_COMPLETE bricks with no topic_id (not yet clustered)
  2. Topics without parent clusters (root-level orphans)
  3. Total topic count and brick-per-topic distribution summary
  4. Nodes with type='brick' and lifecycle='loose' that are overdue for L3

Standalone usage:
    python -m validation.checks.l3_validator
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_REPO_ROOT, ".env"))
except ImportError:
    pass

import psycopg2

from validation.base import NexusValidator

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://nexus:nexus@localhost:5432/nexus")
_AUDIT_DIR = os.path.join(_REPO_ROOT, "audit")


def validate_cluster_integrity(
    batch_id: str = None,
) -> Dict[str, Any]:
    """
    Validate L3 clustering completeness and topic hierarchy.

    Returns:
        Validation report dict with:
          - orphaned_bricks: bricks not assigned to any topic
          - topics_without_parent: root topics with no parent cluster
          - topic_count: total number of topic nodes
          - brick_per_topic_sample: first 10 topic brick counts
          - loose_bricks: bricks still in 'loose' lifecycle (not yet resolved)
    """
    report: Dict[str, Any] = {
        "validation_time": datetime.now(timezone.utc).isoformat(),
        "orphaned_bricks": 0,
        "topics_without_parent": 0,
        "topic_count": 0,
        "loose_bricks": 0,
        "brick_per_topic_sample": [],
        "passed": False,
    }

    validator = NexusValidator(stage="L3", batch_id=batch_id)

    with validator:
        t0 = time.time()
        validator.log("L3_VALIDATION_START", {})

        try:
            conn = psycopg2.connect(DATABASE_URL)

            with conn.cursor() as cur:

                # ── 1. Orphaned bricks in sync.bricks ───────────────────
                # Bricks with no topic_id that have completed L2 — they should
                # have been assigned to a topic by the L3 clustering step.
                try:
                    cur.execute("""
                        SELECT COUNT(*) FROM sync.bricks
                        WHERE topic_id IS NULL
                          AND status = 'L2_COMPLETE'
                    """)
                    report["orphaned_bricks"] = cur.fetchone()[0]
                except Exception as e:
                    report["orphaned_bricks"] = -1
                    validator.log(
                        "L3_VALIDATION_FAIL",
                        {"step": "orphaned_bricks_count", "error": str(e)},
                        status="warn",
                    )

                # ── 2. graph.nodes bricks with loose lifecycle ───────────
                # These are bricks in graph.nodes that are still in 'loose'
                # state — they've been created but not yet resolved/clustered.
                try:
                    cur.execute("""
                        SELECT COUNT(*) FROM graph.nodes
                        WHERE type = 'brick'
                          AND data->>'lifecycle' = 'loose'
                    """)
                    report["loose_bricks"] = cur.fetchone()[0]
                except Exception as e:
                    report["loose_bricks"] = -1
                    validator.log(
                        "L3_VALIDATION_FAIL",
                        {"step": "loose_bricks_count", "error": str(e)},
                        status="warn",
                    )

                # ── 3. Topics without parent cluster ─────────────────────
                # sync.topics with no parent_topic_id — these are root topics.
                # Having some is normal; having ALL topics as roots indicates
                # the L3 hierarchy was never built.
                try:
                    cur.execute("""
                        SELECT COUNT(*) FROM sync.topics
                        WHERE parent_topic_id IS NULL
                    """)
                    report["topics_without_parent"] = cur.fetchone()[0]
                except Exception as e:
                    # Try alternative column name
                    try:
                        cur.execute("""
                            SELECT COUNT(*) FROM sync.topics
                            WHERE parent_id IS NULL
                        """)
                        report["topics_without_parent"] = cur.fetchone()[0]
                    except Exception:
                        report["topics_without_parent"] = -1
                        validator.log(
                            "L3_VALIDATION_FAIL",
                            {"step": "topics_without_parent", "error": str(e)},
                            status="warn",
                        )

                # ── 4. Total topic count ─────────────────────────────────
                try:
                    cur.execute("SELECT COUNT(*) FROM sync.topics")
                    report["topic_count"] = cur.fetchone()[0]
                except Exception:
                    try:
                        cur.execute("SELECT COUNT(*) FROM graph.nodes WHERE type = 'topic'")
                        report["topic_count"] = cur.fetchone()[0]
                    except Exception:
                        report["topic_count"] = -1

                # ── 5. Brick-per-topic sample (top 10 topics by brick count) ─
                try:
                    cur.execute("""
                        SELECT t.display_name, COUNT(b.id) AS brick_count
                        FROM sync.topics t
                        LEFT JOIN sync.bricks b ON b.topic_id = t.id
                        GROUP BY t.id, t.display_name
                        ORDER BY brick_count DESC
                        LIMIT 10
                    """)
                    rows = cur.fetchall()
                    report["brick_per_topic_sample"] = [
                        {"topic": r[0], "brick_count": r[1]} for r in rows
                    ]
                except Exception:
                    report["brick_per_topic_sample"] = []

            conn.close()

        except Exception as e:
            validator.log_error("L3_FAILURE", e, {"step": "db_connection"})
            report["error"] = str(e)
            _save_report(report)
            return report

        # ── Emit audit events for anomalies ─────────────────────────────

        if report["orphaned_bricks"] > 0:
            validator.log(
                "L3_ORPHANED_BRICKS",
                {
                    "count": report["orphaned_bricks"],
                    "note": "Bricks with no topic_id after L2_COMPLETE — L3 clustering may be incomplete",
                },
                status="warn",
            )

        if report["loose_bricks"] > 0:
            validator.log(
                "L3_LOOSE_BRICKS",
                {
                    "count": report["loose_bricks"],
                    "note": "graph.nodes bricks in 'loose' lifecycle — not yet resolved by conflict_resolver",
                },
                status="warn",
            )

        # Topic hierarchy sanity: if all topics have no parent, hierarchy was never built
        total_topics = report["topic_count"]
        no_parent = report["topics_without_parent"]
        if total_topics > 0 and no_parent == total_topics:
            validator.log(
                "L3_FLAT_HIERARCHY",
                {
                    "total_topics": total_topics,
                    "topics_without_parent": no_parent,
                    "note": "All topics are root-level — topic hierarchy may not have been built",
                },
                status="warn",
            )

        # ── Pass/fail ────────────────────────────────────────────────────
        # Pass = no orphaned bricks AND no loose bricks
        orphans = report["orphaned_bricks"]
        loose = report["loose_bricks"]
        passed = (orphans == 0) and (loose == 0)
        report["passed"] = passed

        validator.log_timed(
            "L3_VALIDATION_COMPLETE",
            t0,
            {
                "orphaned_bricks": orphans,
                "loose_bricks": loose,
                "topic_count": total_topics,
                "passed": passed,
            },
            status="ok" if passed else "warn",
        )

    report["audit_summary"] = validator.summary()
    _save_report(report)
    return report


def _save_report(report: Dict[str, Any]):
    os.makedirs(_AUDIT_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(_AUDIT_DIR, f"l3_validation_{ts}.json")
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"[l3_validator] Report saved → {output_path}")
    except Exception as e:
        print(f"[l3_validator] WARN: Could not save report: {e}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _main():
    parser = argparse.ArgumentParser(description="Validate L3 clustering integrity.")
    parser.add_argument("--batch-id", default=None)
    args = parser.parse_args()

    report = validate_cluster_integrity(batch_id=args.batch_id)

    print("\n" + "=" * 60)
    print("L3 CLUSTERING VALIDATION SUMMARY")
    print("=" * 60)
    print(f"  Orphaned bricks (no topic) : {report.get('orphaned_bricks', 'N/A')}")
    print(f"  Loose bricks (unresolved)  : {report.get('loose_bricks', 'N/A')}")
    print(f"  Topics without parent      : {report.get('topics_without_parent', 'N/A')}")
    print(f"  Total topics               : {report.get('topic_count', 'N/A')}")
    print(f"  Passed                     : {'✅ YES' if report.get('passed') else '⚠️  NO'}")

    sample = report.get("brick_per_topic_sample", [])
    if sample:
        print("\n  Top topics by brick count:")
        for entry in sample[:5]:
            print(f"    {entry.get('topic', 'Unknown'):<40} {entry.get('brick_count'):>5} bricks")
    print("=" * 60)

    sys.exit(0 if report.get("passed") else 1)


if __name__ == "__main__":
    _main()
