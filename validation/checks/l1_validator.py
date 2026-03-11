"""
validation/checks/l1_validator.py
==================================
L1 Extraction Audit — validates that all source messages were ingested into
graph.nodes after the L1 (Ollama) processing stage.

Checks:
  1. Count messages across all openaiconversations/messages_batch_*.json files
  2. Count graph.nodes rows (all types, since L1 creates nodes per message)
  3. Count specifically status='L1_COMPLETE' nodes
  4. Report discrepancies

Standalone usage:
    python -m validation.checks.l1_validator
    python -m validation.checks.l1_validator --batch-dir openaiconversations
"""

import argparse
import glob
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

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


def count_source_messages(batch_dir: str) -> Dict[str, Any]:
    """
    Count total messages across all messages_batch_*.json files.

    Returns:
        {
          "batch_dir": str,
          "batch_files": int,
          "total_messages": int,
          "per_batch": { "messages_batch_1.json": 412, ... }
        }
    """
    pattern = os.path.join(batch_dir, "messages_batch_*.json")
    files = sorted(glob.glob(pattern))

    total = 0
    per_batch: Dict[str, int] = {}

    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            count = len(data) if isinstance(data, list) else 0
            per_batch[os.path.basename(fp)] = count
            total += count
        except Exception as e:
            per_batch[os.path.basename(fp)] = -1  # -1 = unreadable
            print(f"[l1_validator] WARN: Could not read {fp}: {e}")

    return {
        "batch_dir": batch_dir,
        "batch_files": len(files),
        "total_messages": total,
        "per_batch": per_batch,
    }


def count_db_nodes(database_url: str) -> Dict[str, Any]:
    """
    Count nodes in graph.nodes, broken down by status.
    """
    result = {
        "total_nodes": 0,
        "l1_complete": 0,
        "l2_complete": 0,
        "no_status": 0,
        "error": None,
    }
    try:
        conn = psycopg2.connect(database_url)
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM graph.nodes")
            result["total_nodes"] = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM graph.nodes WHERE status = 'L1_COMPLETE'")
            result["l1_complete"] = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM graph.nodes WHERE status = 'L2_COMPLETE'")
            result["l2_complete"] = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM graph.nodes WHERE status IS NULL")
            result["no_status"] = cur.fetchone()[0]

        conn.close()
    except Exception as e:
        result["error"] = str(e)
        print(f"[l1_validator] WARN: DB query failed: {e}")

    return result


def validate_l1_counts(
    batch_dir: str = "openaiconversations",
    batch_id: str = None,
) -> Dict[str, Any]:
    """
    Full L1 validation: compare source message count to DB node count.

    Args:
        batch_dir: Directory containing messages_batch_*.json files
        batch_id:  Optional batch ID for audit trail correlation

    Returns:
        Validation report dict.
    """
    report: Dict[str, Any] = {
        "validation_time": datetime.now(timezone.utc).isoformat(),
        "batch_dir": batch_dir,
        "source": {},
        "database": {},
        "delta": None,
        "passed": False,
    }

    validator = NexusValidator(stage="L1", batch_id=batch_id)

    with validator:
        t0 = time.time()
        validator.log("L1_VALIDATION_START", {"batch_dir": batch_dir})

        # ── Count source messages ────────────────────────────────────────
        t_src = time.time()
        source = count_source_messages(batch_dir)
        report["source"] = source
        validator.log_timed(
            "SOURCE_COUNT_COMPLETE",
            t_src,
            {
                "batch_files": source["batch_files"],
                "total_messages": source["total_messages"],
            },
        )

        # ── Count DB nodes ───────────────────────────────────────────────
        t_db = time.time()
        db_counts = count_db_nodes(DATABASE_URL)
        report["database"] = db_counts
        validator.log_timed(
            "DB_COUNT_COMPLETE",
            t_db,
            {
                "total_nodes": db_counts["total_nodes"],
                "l1_complete": db_counts["l1_complete"],
            },
            status="error" if db_counts.get("error") else "ok",
        )

        # ── Compare counts ───────────────────────────────────────────────
        src_count = source["total_messages"]
        db_count = db_counts["total_nodes"]
        delta = db_count - src_count
        report["delta"] = delta

        if db_counts.get("error"):
            validator.log(
                "L1_VALIDATION_FAIL",
                {"reason": "DB connection error", "error": db_counts["error"]},
                status="error",
            )
            report["passed"] = False

        elif src_count == 0:
            validator.log(
                "L1_VALIDATION_FAIL",
                {"reason": "No source batch files found", "batch_dir": batch_dir},
                status="error",
            )
            report["passed"] = False

        elif delta == 0:
            validator.log_timed(
                "L1_VALIDATION_PASSED",
                t0,
                {"source_count": src_count, "db_count": db_count},
            )
            report["passed"] = True

        else:
            # Delta != 0 — warn but don't hard-fail (DB may have more nodes from
            # other sources, or L1 may be partially complete)
            status = "warn" if delta > 0 else "error"
            validator.log_timed(
                "L1_COUNT_MISMATCH",
                t0,
                {
                    "source_count": src_count,
                    "db_count": db_count,
                    "delta": delta,
                    "note": "Positive delta: DB has more nodes than source (OK if other data exists). "
                            "Negative delta: source messages not yet ingested into DB.",
                },
                status=status,
            )
            # Treat as passed if DB has >= source (i.e., at least all messages ingested)
            report["passed"] = db_count >= src_count

    # ── Save report ──────────────────────────────────────────────────────
    report["audit_summary"] = validator.summary()
    _save_report(report)

    return report


def _save_report(report: Dict[str, Any]):
    os.makedirs(_AUDIT_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(_AUDIT_DIR, f"l1_validation_{ts}.json")
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"[l1_validator] Report saved → {output_path}")
    except Exception as e:
        print(f"[l1_validator] WARN: Could not save report: {e}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _main():
    parser = argparse.ArgumentParser(description="Validate L1 extraction counts.")
    parser.add_argument("--batch-dir", default="openaiconversations")
    parser.add_argument("--batch-id", default=None)
    args = parser.parse_args()

    report = validate_l1_counts(args.batch_dir, batch_id=args.batch_id)

    print("\n" + "=" * 60)
    print("L1 VALIDATION SUMMARY")
    print("=" * 60)
    src = report.get("source", {})
    db = report.get("database", {})
    print(f"  Batch files     : {src.get('batch_files', 0)}")
    print(f"  Source messages : {src.get('total_messages', 0)}")
    print(f"  DB nodes total  : {db.get('total_nodes', 0)}")
    print(f"  L1_COMPLETE     : {db.get('l1_complete', 0)}")
    print(f"  L2_COMPLETE     : {db.get('l2_complete', 0)}")
    print(f"  Delta (DB-src)  : {report.get('delta', 'N/A')}")
    print(f"  Passed          : {'✅ YES' if report.get('passed') else '⚠️  NO'}")
    print("=" * 60)

    sys.exit(0 if report.get("passed") else 1)


if __name__ == "__main__":
    _main()
