"""
validation/checks/preprocess.py
================================
Input validation for conversations.json before splitting.

Standalone usage:
    python -m validation.checks.preprocess --input conversations.json
    python -m validation.checks.preprocess --input local/conversations.json.json
"""

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Path bootstrap — works whether run as module or script
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_REPO_ROOT, ".env"))
except ImportError:
    pass

from validation.base import NexusValidator

# Required fields every conversation must have
_REQUIRED_FIELDS = ["id", "title", "mapping"]
# Output directory for audit reports
_AUDIT_DIR = os.path.join(_REPO_ROOT, "audit")


def validate_conversations_json(
    input_file: str,
    batch_id: str = None,
) -> Dict[str, Any]:
    """
    Validate the structure of a conversations.json export.

    Steps:
      1. Verify file exists and is valid JSON.
      2. Check that root is a list.
      3. For each conversation, verify required fields are present.
      4. Generate SHA-256 checksum of the full file.
      5. Save report to audit/input_validation_<stem>.json.
      6. Emit audit events via NexusValidator.

    Args:
        input_file: Path to conversations.json (or any variant)
        batch_id:   Optional batch identifier for audit trail correlation

    Returns:
        Validation report dict.
    """
    input_path = Path(input_file)
    stem = input_path.stem

    report: Dict[str, Any] = {
        "validation_time": datetime.now(timezone.utc).isoformat(),
        "file": str(input_path),
        "total_conversations": 0,
        "malformed_entries": [],
        "missing_field_summary": {},
        "checksum_sha256": None,
        "passed": False,
    }

    validator = NexusValidator(stage="PRE", batch_id=batch_id)

    with validator:
        t0 = time.time()
        validator.log("PREPROCESS_VALIDATION_START", {"input_file": str(input_path)})

        # ── 1. File existence check ──────────────────────────────────────
        if not input_path.exists():
            validator.log_error(
                "VALIDATION_FAIL",
                FileNotFoundError(f"Input file not found: {input_path}"),
                {"input_file": str(input_path)},
            )
            report["error"] = f"File not found: {input_path}"
            _save_report(report, stem)
            return report

        # ── 2. SHA-256 checksum ──────────────────────────────────────────
        try:
            t_chk = time.time()
            raw_bytes = input_path.read_bytes()
            checksum = hashlib.sha256(raw_bytes).hexdigest()
            report["checksum_sha256"] = checksum
            report["file_size_bytes"] = len(raw_bytes)
            validator.log_timed(
                "CHECKSUM_COMPUTED",
                t_chk,
                {"checksum_sha256": checksum, "file_size_bytes": len(raw_bytes)},
            )
        except Exception as e:
            validator.log_error("VALIDATION_FAIL", e, {"step": "checksum"})

        # ── 3. JSON parse ────────────────────────────────────────────────
        try:
            t_parse = time.time()
            with open(input_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            validator.log_timed("JSON_PARSED", t_parse, {"type": type(data).__name__})
        except json.JSONDecodeError as e:
            validator.log_error(
                "VALIDATION_FAIL", e, {"step": "json_parse", "error": str(e)}
            )
            report["error"] = f"JSON parse error: {e}"
            _save_report(report, stem)
            return report

        # ── 4. Root type check ───────────────────────────────────────────
        if not isinstance(data, list):
            validator.log(
                "VALIDATION_FAIL",
                {"expected": "list", "got": type(data).__name__},
                status="error",
            )
            report["error"] = f"Expected root list, got {type(data).__name__}"
            _save_report(report, stem)
            return report

        report["total_conversations"] = len(data)
        validator.log(
            "CONVERSATIONS_COUNTED",
            {"total": len(data)},
        )

        # ── 5. Field validation per conversation ─────────────────────────
        missing_field_counts: Dict[str, int] = {}
        malformed: List[Dict] = []

        for idx, conv in enumerate(data):
            if not isinstance(conv, dict):
                malformed.append({"index": idx, "error": "not a dict"})
                validator.log(
                    "INVALID_MESSAGE",
                    {"index": idx, "error": "conversation entry is not a dict"},
                    status="warn",
                )
                continue

            missing = [f for f in _REQUIRED_FIELDS if f not in conv]
            if missing:
                entry = {"index": idx, "missing_fields": missing}
                # Include conversation id if available for traceability
                if "id" in conv:
                    entry["conversation_id"] = conv["id"]
                elif "conversation_id" in conv:
                    entry["conversation_id"] = conv["conversation_id"]
                malformed.append(entry)
                for field in missing:
                    missing_field_counts[field] = missing_field_counts.get(field, 0) + 1
                validator.log(
                    "INVALID_MESSAGE",
                    {"index": idx, "missing_fields": missing},
                    status="warn",
                )

        report["malformed_entries"] = malformed
        report["missing_field_summary"] = missing_field_counts
        report["malformed_count"] = len(malformed)
        report["valid_count"] = len(data) - len(malformed)

        passed = len(malformed) == 0
        report["passed"] = passed

        validator.log_timed(
            "PREPROCESS_VALIDATION_COMPLETE",
            t0,
            {
                "total": len(data),
                "valid": report["valid_count"],
                "malformed": report["malformed_count"],
                "passed": passed,
            },
            status="ok" if passed else "warn",
        )

    # ── 6. Save report ───────────────────────────────────────────────────
    report["audit_summary"] = validator.summary()
    _save_report(report, stem)

    return report


def _save_report(report: Dict[str, Any], stem: str):
    """Persist the validation report to audit/ directory."""
    os.makedirs(_AUDIT_DIR, exist_ok=True)
    output_path = os.path.join(_AUDIT_DIR, f"input_validation_{stem}.json")
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"[preprocess] Report saved → {output_path}")
    except Exception as e:
        print(f"[preprocess] WARN: Could not save report: {e}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _main():
    parser = argparse.ArgumentParser(
        description="Validate conversations.json before pipeline processing."
    )
    parser.add_argument(
        "--input",
        default="conversations.json",
        help="Path to the conversations.json file (default: conversations.json)",
    )
    parser.add_argument(
        "--batch-id",
        default=None,
        help="Optional batch ID to correlate with other audit events",
    )
    args = parser.parse_args()

    report = validate_conversations_json(args.input, batch_id=args.batch_id)

    print("\n" + "=" * 60)
    print("PREPROCESSING VALIDATION SUMMARY")
    print("=" * 60)
    print(f"  File           : {report.get('file')}")
    print(f"  Total convs    : {report.get('total_conversations', 0)}")
    print(f"  Valid          : {report.get('valid_count', 0)}")
    print(f"  Malformed      : {report.get('malformed_count', 0)}")
    print(f"  Checksum (SHA256): {report.get('checksum_sha256', 'N/A')[:16]}...")
    print(f"  Passed         : {'✅ YES' if report.get('passed') else '⚠️  NO (see audit/ report)'}")
    print("=" * 60)

    if report.get("malformed_entries"):
        print(f"\nFirst 5 malformed entries:")
        for entry in report["malformed_entries"][:5]:
            print(f"  idx={entry.get('index')} missing={entry.get('missing_fields')}")

    sys.exit(0 if report.get("passed") else 1)


if __name__ == "__main__":
    _main()
