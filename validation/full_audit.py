"""
validation/full_audit.py
=========================
Full Pipeline Audit Orchestrator — runs all validation stages in sequence
and produces a consolidated JSON report.

Stages executed:
  PRE  → validate_conversations_json()    (input integrity)
  L1   → validate_l1_counts()             (extraction coverage)
  L2   → validate_l2_synthesis()          (embedding completeness)
  L3   → validate_cluster_integrity()     (clustering / topic hierarchy)
  POST → system checksums + trail summary

Called by:
  python scripts/run_validation.py [options]
"""

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

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

from validation.base import NexusValidator
from validation.checks.preprocess import validate_conversations_json
from validation.checks.l1_validator import validate_l1_counts
from validation.checks.l2_validator import validate_l2_synthesis
from validation.checks.l3_validator import validate_cluster_integrity

_AUDIT_DIR = os.path.join(_REPO_ROOT, "audit")
_ARCHIVE_DIR = os.path.join(_AUDIT_DIR, "archive")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _file_checksum(path: str) -> str:
    """SHA-256 checksum of a file. Returns 'missing' if file not found."""
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except FileNotFoundError:
        return "missing"
    except Exception as e:
        return f"error:{e}"


def _get_ollama_model_info() -> Dict[str, Any]:
    """
    Retrieve the currently active Ollama model from environment.
    Does NOT call the Ollama API — avoids network dependency at audit time.
    """
    return {
        "model": os.environ.get("LOCAL_LLM_MODEL", "phi3:latest"),
        "host": os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434"),
        "provider": os.environ.get("LOCAL_LLM_PROVIDER", "ollama"),
    }


def _get_openai_model_info() -> Dict[str, Any]:
    return {
        "model": os.environ.get("OPENAI_MODEL", "text-embedding-3-small"),
        "api_key_set": bool(os.environ.get("OPENAI_API_KEY")),
    }


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def full_pipeline_audit(
    input_file: str = "conversations.json",
    batch_dir: str = "openaiconversations",
    run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run all validation stages and return a consolidated audit report.

    Args:
        input_file: Path to conversations.json
        batch_dir:  Directory containing messages_batch_*.json files
        run_id:     Optional identifier for this full audit run

    Returns:
        Consolidated report dict saved to audit/full_audit_<timestamp>.json
    """
    run_id = run_id or f"audit-{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    t_total = time.time()

    master_report: Dict[str, Any] = {
        "run_id": run_id,
        "audit_time": datetime.now(timezone.utc).isoformat(),
        "input_file": input_file,
        "batch_dir": batch_dir,
        "stages": {},
        "system_checksums": {},
        "model_info": {},
        "overall_passed": False,
        "total_duration_ms": None,
    }

    # ── POST validator for overall trail ────────────────────────────────
    post_validator = NexusValidator(stage="POST", batch_id=run_id)
    post_validator._open_db()
    post_validator.log("FULL_AUDIT_START", {"run_id": run_id, "input_file": input_file})

    # ====================================================================
    # Stage PRE — Input validation
    # ====================================================================
    print("\n" + "─" * 60)
    print("STAGE PRE: Input Validation")
    print("─" * 60)
    try:
        t = time.time()
        pre_report = validate_conversations_json(input_file, batch_id=run_id)
        master_report["stages"]["pre"] = {
            "passed": pre_report.get("passed", False),
            "duration_ms": int((time.time() - t) * 1000),
            "total_conversations": pre_report.get("total_conversations", 0),
            "malformed_count": pre_report.get("malformed_count", 0),
            "checksum_sha256": pre_report.get("checksum_sha256"),
        }
        post_validator.log(
            "STAGE_PRE_COMPLETE",
            master_report["stages"]["pre"],
            status="ok" if pre_report.get("passed") else "warn",
        )
    except Exception as e:
        master_report["stages"]["pre"] = {"passed": False, "error": str(e)}
        post_validator.log_error("STAGE_PRE_FAILED", e)

    # ====================================================================
    # Stage L1 — Extraction count validation
    # ====================================================================
    print("\n" + "─" * 60)
    print("STAGE L1: Extraction Count Validation")
    print("─" * 60)
    try:
        t = time.time()
        l1_report = validate_l1_counts(batch_dir, batch_id=run_id)
        master_report["stages"]["l1"] = {
            "passed": l1_report.get("passed", False),
            "duration_ms": int((time.time() - t) * 1000),
            "source_messages": l1_report.get("source", {}).get("total_messages", 0),
            "db_nodes": l1_report.get("database", {}).get("total_nodes", 0),
            "l1_complete": l1_report.get("database", {}).get("l1_complete", 0),
            "delta": l1_report.get("delta"),
        }
        post_validator.log(
            "STAGE_L1_COMPLETE",
            master_report["stages"]["l1"],
            status="ok" if l1_report.get("passed") else "warn",
        )
    except Exception as e:
        master_report["stages"]["l1"] = {"passed": False, "error": str(e)}
        post_validator.log_error("STAGE_L1_FAILED", e)

    # ====================================================================
    # Stage L2 — Embedding / synthesis validation
    # ====================================================================
    print("\n" + "─" * 60)
    print("STAGE L2: Synthesis Validation")
    print("─" * 60)
    try:
        t = time.time()
        l2_report = validate_l2_synthesis(batch_id=run_id)
        master_report["stages"]["l2"] = {
            "passed": l2_report.get("passed", False),
            "duration_ms": int((time.time() - t) * 1000),
            "nodes_l2_complete": l2_report.get("nodes_l2_complete", 0),
            "nodes_pending": l2_report.get("nodes_l1_complete", 0),
            "stalled": l2_report.get("nodes_stalled_l2", 0),
            "node_brick_delta": l2_report.get("node_brick_delta"),
        }
        post_validator.log(
            "STAGE_L2_COMPLETE",
            master_report["stages"]["l2"],
            status="ok" if l2_report.get("passed") else "warn",
        )
    except Exception as e:
        master_report["stages"]["l2"] = {"passed": False, "error": str(e)}
        post_validator.log_error("STAGE_L2_FAILED", e)

    # ====================================================================
    # Stage L3 — Clustering / topic hierarchy validation
    # ====================================================================
    print("\n" + "─" * 60)
    print("STAGE L3: Clustering Validation")
    print("─" * 60)
    try:
        t = time.time()
        l3_report = validate_cluster_integrity(batch_id=run_id)
        master_report["stages"]["l3"] = {
            "passed": l3_report.get("passed", False),
            "duration_ms": int((time.time() - t) * 1000),
            "orphaned_bricks": l3_report.get("orphaned_bricks", 0),
            "loose_bricks": l3_report.get("loose_bricks", 0),
            "topic_count": l3_report.get("topic_count", 0),
        }
        post_validator.log(
            "STAGE_L3_COMPLETE",
            master_report["stages"]["l3"],
            status="ok" if l3_report.get("passed") else "warn",
        )
    except Exception as e:
        master_report["stages"]["l3"] = {"passed": False, "error": str(e)}
        post_validator.log_error("STAGE_L3_FAILED", e)

    # ====================================================================
    # System checksums
    # ====================================================================
    master_report["system_checksums"] = {
        "splitter":    _file_checksum(os.path.join(_REPO_ROOT, "scripts", "split_conversations.py")),
        "l2_backfill": _file_checksum(os.path.join(_REPO_ROOT, "scripts", "run_l2_backfill.py")),
        "l3_runner":   _file_checksum(os.path.join(_REPO_ROOT, "scripts", "run_l3_clustering.py")),
        "full_audit":  _file_checksum(os.path.join(_REPO_ROOT, "validation", "full_audit.py")),
    }

    master_report["model_info"] = {
        "l1_model": _get_ollama_model_info(),
        "l2_model": _get_openai_model_info(),
    }

    # ====================================================================
    # Overall pass/fail
    # ====================================================================
    stage_results = [v.get("passed", False) for v in master_report["stages"].values()]
    overall_passed = all(stage_results)
    master_report["overall_passed"] = overall_passed
    master_report["total_duration_ms"] = int((time.time() - t_total) * 1000)

    # ── Final audit trail entry ──────────────────────────────────────────
    try:
        post_validator.log_timed(
            "FULL_AUDIT_COMPLETE",
            t_total,
            {
                "run_id": run_id,
                "overall_passed": overall_passed,
                "stages_passed": sum(stage_results),
                "stages_total": len(stage_results),
            },
            status="ok" if overall_passed else "warn",
        )
        post_validator._close_db()
    except Exception:
        pass

    # ====================================================================
    # Save reports
    # ====================================================================
    _save_master_report(master_report, run_id)

    return master_report


def _save_master_report(report: Dict[str, Any], run_id: str):
    """Save to audit/ and also archive a copy."""
    os.makedirs(_AUDIT_DIR, exist_ok=True)
    os.makedirs(_ARCHIVE_DIR, exist_ok=True)

    filename = f"full_audit_{run_id}.json"
    primary = os.path.join(_AUDIT_DIR, filename)
    archive = os.path.join(_ARCHIVE_DIR, filename)

    content = json.dumps(report, indent=2, ensure_ascii=False)

    try:
        with open(primary, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"\n[full_audit] Report saved → {primary}")
    except Exception as e:
        print(f"[full_audit] WARN: Could not save primary report: {e}")

    # Archive copy (separate directory — for archiving artifacts)
    try:
        with open(archive, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[full_audit] Archived   → {archive}")
    except Exception as e:
        print(f"[full_audit] WARN: Could not save archive: {e}")

    # TODO: PDF generation — currently JSON only.
    # TODO: CI/CD — attach report as build artifact.
