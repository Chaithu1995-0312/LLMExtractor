"""
validation/checks/l2_validator.py
==================================
L2 Synthesis Audit — validates that L1_COMPLETE nodes have been promoted to
L2_COMPLETE (embedding + sync.bricks creation) correctly.

Checks:
  1. Count nodes with status='L1_COMPLETE' (pending L2)
  2. Count nodes with status='L2_COMPLETE' (embedding done)
  3. Count sync.bricks rows mirrored from L2
  4. Check for nodes where l2_started_at is set but l2_completed_at is NULL
     (stalled mid-L2)
  5. Validate individual brick structure via L2Validator.validate_brick()

Standalone usage:
    python -m validation.checks.l2_validator
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

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

# Fields that every brick dict must contain to be considered valid
_BRICK_REQUIRED_FIELDS = ("id", "content")


class L2Validator(NexusValidator):
    """
    L2-specific validator with a per-brick validation method, designed to be
    called inline from run_l2_backfill.py.

    Usage in run_l2_backfill.py:
        from validation.checks.l2_validator import L2Validator
        validator = L2Validator()
        # ...
        if not validator.validate_brick(brick_dict):
            log.warning(f"Invalid brick {brick_dict.get('id')}")
            continue
        save_to_db(brick_dict)
    """

    def __init__(self, batch_id: str = None, strict: bool = False):
        super().__init__(stage="L2", batch_id=batch_id, strict=strict)
        self._invalid_bricks: List[Dict] = []

    def validate_brick(self, brick: Dict[str, Any]) -> bool:
        """
        Validate a single brick dict before it is saved to the DB.

        Rules:
          - Must be a dict
          - Must have 'id' and 'content' fields
          - 'content' must not be empty string after strip

        Args:
            brick: Dict representing a knowledge brick

        Returns:
            True if valid, False if invalid (logs INVALID_MESSAGE event)
        """
        if not isinstance(brick, dict):
            self.log(
                "INVALID_MESSAGE",
                {"error": "brick is not a dict", "type": type(brick).__name__},
                status="warn",
            )
            self._invalid_bricks.append({"error": "not_a_dict"})
            return False

        missing = [f for f in _BRICK_REQUIRED_FIELDS if not brick.get(f)]
        if missing:
            self.log(
                "INVALID_MESSAGE",
                {
                    "brick_id": brick.get("id", "unknown"),
                    "missing_fields": missing,
                },
                status="warn",
            )
            self._invalid_bricks.append({"brick_id": brick.get("id"), "missing": missing})
            return False

        # Content must not be purely whitespace
        if not str(brick.get("content", "")).strip():
            self.log(
                "INVALID_MESSAGE",
                {"brick_id": brick.get("id"), "error": "empty content"},
                status="warn",
            )
            self._invalid_bricks.append({"brick_id": brick.get("id"), "error": "empty_content"})
            return False

        return True

    def invalid_brick_summary(self) -> Dict[str, Any]:
        return {
            "total_invalid": len(self._invalid_bricks),
            "samples": self._invalid_bricks[:10],
        }


def validate_l2_synthesis(
    batch_id: str = None,
) -> Dict[str, Any]:
    """
    Full L2 pipeline validation.

    Returns:
        Validation report dict.
    """
    report: Dict[str, Any] = {
        "validation_time": datetime.now(timezone.utc).isoformat(),
        "nodes_l1_complete": 0,
        "nodes_l2_complete": 0,
        "nodes_stalled_l2": 0,
        "sync_bricks_count": 0,
        "node_brick_delta": None,
        "latest_l2_timestamp": None,
        "passed": False,
    }

    validator = NexusValidator(stage="L2", batch_id=batch_id)

    with validator:
        t0 = time.time()
        validator.log("L2_VALIDATION_START", {})

        try:
            conn = psycopg2.connect(DATABASE_URL)

            with conn.cursor() as cur:
                # 1. Nodes pending L2
                cur.execute("SELECT COUNT(*) FROM graph.nodes WHERE status = 'L1_COMPLETE'")
                report["nodes_l1_complete"] = cur.fetchone()[0]

                # 2. Nodes completed L2
                cur.execute("SELECT COUNT(*) FROM graph.nodes WHERE status = 'L2_COMPLETE'")
                report["nodes_l2_complete"] = cur.fetchone()[0]

                # 3. Stalled nodes (L2 started but never completed)
                cur.execute("""
                    SELECT COUNT(*) FROM graph.nodes
                    WHERE l2_started_at IS NOT NULL
                      AND l2_completed_at IS NULL
                      AND status != 'L2_COMPLETE'
                """)
                report["nodes_stalled_l2"] = cur.fetchone()[0]

                # 4. sync.bricks count
                try:
                    cur.execute("SELECT COUNT(*) FROM sync.bricks WHERE status = 'L2_COMPLETE'")
                    report["sync_bricks_count"] = cur.fetchone()[0]
                except Exception:
                    report["sync_bricks_count"] = -1  # table may not exist yet

                # 5. Latest L2 completion timestamp
                cur.execute("SELECT MAX(l2_completed_at) FROM graph.nodes WHERE status = 'L2_COMPLETE'")
                ts = cur.fetchone()[0]
                report["latest_l2_timestamp"] = str(ts) if ts else None

            conn.close()

        except Exception as e:
            validator.log_error("L2_FAILURE", e, {"step": "db_query"})
            report["error"] = str(e)
            _save_report(report)
            return report

        # ── Node-brick delta ─────────────────────────────────────────────
        l2_nodes = report["nodes_l2_complete"]
        bricks = report["sync_bricks_count"]
        if bricks >= 0:
            delta = l2_nodes - bricks
            report["node_brick_delta"] = delta
            if delta != 0:
                validator.log(
                    "L2_COUNT_MISMATCH",
                    {
                        "l2_nodes": l2_nodes,
                        "sync_bricks": bricks,
                        "delta": delta,
                        "note": "sync.bricks may lag graph.nodes due to async mirror writes",
                    },
                    status="warn",
                )

        # ── Stalled nodes warning ────────────────────────────────────────
        if report["nodes_stalled_l2"] > 0:
            validator.log(
                "L2_STALLED_NODES",
                {
                    "count": report["nodes_stalled_l2"],
                    "note": "Nodes with l2_started_at but no l2_completed_at — re-run backfill",
                },
                status="warn",
            )

        # ── Pass/fail determination ──────────────────────────────────────
        pending = report["nodes_l1_complete"]
        passed = pending == 0  # All L1_COMPLETE nodes should be promoted
        report["passed"] = passed

        validator.log_timed(
            "L2_VALIDATION_COMPLETE",
            t0,
            {
                "pending_l2": pending,
                "completed_l2": l2_nodes,
                "stalled": report["nodes_stalled_l2"],
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
    output_path = os.path.join(_AUDIT_DIR, f"l2_validation_{ts}.json")
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"[l2_validator] Report saved → {output_path}")
    except Exception as e:
        print(f"[l2_validator] WARN: Could not save report: {e}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _main():
    parser = argparse.ArgumentParser(description="Validate L2 synthesis counts.")
    parser.add_argument("--batch-id", default=None)
    args = parser.parse_args()

    report = validate_l2_synthesis(batch_id=args.batch_id)

    print("\n" + "=" * 60)
    print("L2 SYNTHESIS VALIDATION SUMMARY")
    print("=" * 60)
    print(f"  Pending L2 (L1_COMPLETE)  : {report.get('nodes_l1_complete', 0)}")
    print(f"  Done L2 (L2_COMPLETE)     : {report.get('nodes_l2_complete', 0)}")
    print(f"  Stalled L2                : {report.get('nodes_stalled_l2', 0)}")
    print(f"  sync.bricks (L2_COMPLETE) : {report.get('sync_bricks_count', 'N/A')}")
    print(f"  Node-brick delta          : {report.get('node_brick_delta', 'N/A')}")
    print(f"  Latest L2 timestamp       : {report.get('latest_l2_timestamp', 'N/A')}")
    print(f"  Passed                    : {'✅ YES' if report.get('passed') else '⚠️  NO (pending nodes exist)'}")
    print("=" * 60)

    sys.exit(0 if report.get("passed") else 1)


if __name__ == "__main__":
    _main()
