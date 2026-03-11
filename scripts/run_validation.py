#!/usr/bin/env python3
"""
scripts/run_validation.py
==========================
CLI entry point for the Nexus Cognitive Pipeline Validation Framework.

Runs one or all validation stages and prints a final summary.

Usage:
    # Full pipeline audit (all stages)
    python scripts/run_validation.py

    # Single stage
    python scripts/run_validation.py --stage pre  --input conversations.json
    python scripts/run_validation.py --stage l1   --batch-dir openaiconversations
    python scripts/run_validation.py --stage l2
    python scripts/run_validation.py --stage l3

    # Full audit with custom paths
    python scripts/run_validation.py --stage all --input local/conversations.json.json --output audit/my_report.json

    # Apply DB schema migration first (run once before validation)
    python scripts/run_validation.py --migrate
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_REPO_ROOT, ".env"))
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Lazy imports — only load what's needed for the requested stage
# ---------------------------------------------------------------------------

def _run_migrate():
    """Apply the audit schema migration. Safe to re-run (idempotent)."""
    print("[run_validation] Applying DB migration: 20240628_audit_tables...")
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "migration_audit",
            os.path.join(_REPO_ROOT, "scripts", "migrations", "20240628_audit_tables.py"),
        )
        mod = importlib.util.load_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.upgrade()
        print("[run_validation] ✅ Migration applied.")
    except Exception as e:
        print(f"[run_validation] ❌ Migration failed: {e}")
        sys.exit(1)


def _run_pre(input_file: str, batch_id: str = None):
    from validation.checks.preprocess import validate_conversations_json
    return validate_conversations_json(input_file, batch_id=batch_id)


def _run_l1(batch_dir: str, batch_id: str = None):
    from validation.checks.l1_validator import validate_l1_counts
    return validate_l1_counts(batch_dir, batch_id=batch_id)


def _run_l2(batch_id: str = None):
    from validation.checks.l2_validator import validate_l2_synthesis
    return validate_l2_synthesis(batch_id=batch_id)


def _run_l3(batch_id: str = None):
    from validation.checks.l3_validator import validate_cluster_integrity
    return validate_cluster_integrity(batch_id=batch_id)


def _run_all(input_file: str, batch_dir: str, output: str = None):
    from validation.full_audit import full_pipeline_audit
    run_id = f"audit-{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    report = full_pipeline_audit(
        input_file=input_file,
        batch_dir=batch_dir,
        run_id=run_id,
    )
    if output:
        os.makedirs(os.path.dirname(os.path.abspath(output)), exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"[run_validation] Report also written to: {output}")
    return report


# ---------------------------------------------------------------------------
# Summary printer
# ---------------------------------------------------------------------------

def _print_summary(stage: str, report: dict):
    passed = report.get("passed", report.get("overall_passed", False))
    status_icon = "✅" if passed else "⚠️ "
    print("\n" + "=" * 60)
    print(f"VALIDATION SUMMARY — STAGE: {stage.upper()}")
    print("=" * 60)

    if stage == "all":
        stages = report.get("stages", {})
        for s, d in stages.items():
            s_icon = "✅" if d.get("passed") else "⚠️ "
            duration = d.get("duration_ms", "?")
            print(f"  {s_icon} {s.upper():<6} | passed={d.get('passed')} | {duration}ms")
        print(f"\n  Overall   : {status_icon} {'PASSED' if passed else 'WARNINGS/FAILURES'}")
        print(f"  Total time: {report.get('total_duration_ms', '?')}ms")
        print(f"  Run ID    : {report.get('run_id', 'N/A')}")
    else:
        for k, v in report.items():
            if k not in ("malformed_entries", "per_batch", "brick_per_topic_sample", "audit_summary"):
                print(f"  {k}: {v}")
        print(f"\n  Result: {status_icon} {'PASSED' if passed else 'NOT FULLY PASSED'}")

    print("=" * 60)
    return passed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Nexus Cognitive Pipeline Validation Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_validation.py                           # full audit
  python scripts/run_validation.py --stage pre               # input validation only
  python scripts/run_validation.py --stage l1                # L1 counts only
  python scripts/run_validation.py --stage l2                # L2 synthesis only
  python scripts/run_validation.py --stage l3                # L3 clustering only
  python scripts/run_validation.py --migrate                 # apply DB migration
  python scripts/run_validation.py --output audit/report.json  # save full report
        """,
    )
    parser.add_argument(
        "--stage",
        choices=["all", "pre", "l1", "l2", "l3"],
        default="all",
        help="Validation stage to run (default: all)",
    )
    parser.add_argument(
        "--input",
        default="conversations.json",
        help="Path to conversations.json (used by PRE stage)",
    )
    parser.add_argument(
        "--batch-dir",
        default="openaiconversations",
        help="Directory containing messages_batch_*.json files (used by L1 stage)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional path to write the full audit JSON report",
    )
    parser.add_argument(
        "--migrate",
        action="store_true",
        help="Apply the audit DB schema migration (20240628_audit_tables.py) and exit",
    )
    parser.add_argument(
        "--batch-id",
        default=None,
        help="Optional batch ID to correlate audit events across stages",
    )

    args = parser.parse_args()

    # ── Migration mode ───────────────────────────────────────────────────
    if args.migrate:
        _run_migrate()
        sys.exit(0)

    # ── Stage dispatch ───────────────────────────────────────────────────
    stage = args.stage
    passed = False

    try:
        if stage == "pre":
            report = _run_pre(args.input, batch_id=args.batch_id)
            passed = _print_summary(stage, report)

        elif stage == "l1":
            report = _run_l1(args.batch_dir, batch_id=args.batch_id)
            passed = _print_summary(stage, report)

        elif stage == "l2":
            report = _run_l2(batch_id=args.batch_id)
            passed = _print_summary(stage, report)

        elif stage == "l3":
            report = _run_l3(batch_id=args.batch_id)
            passed = _print_summary(stage, report)

        elif stage == "all":
            report = _run_all(args.input, args.batch_dir, output=args.output)
            passed = _print_summary(stage, report)

    except KeyboardInterrupt:
        print("\n[run_validation] Interrupted by user.")
        sys.exit(130)

    except Exception as e:
        print(f"\n[run_validation] ❌ Unexpected error in stage '{stage}': {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)

    # Exit code: 0 = passed, 1 = validation issues found
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
