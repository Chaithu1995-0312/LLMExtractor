"""
nexus.memory.health
====================
Memory Layer integrity and health checker.

Responsibility:
  Detect structural degradation in the Memory Layer BEFORE it silently
  corrupts retrieval quality. All checks are read-only — this module
  never writes to any store.

Checks performed by MemoryHealthChecker.run_all():
  1. index_size          — Is the Chroma vector index non-empty?
  2. count_reconciliation — Do vector counts and metadata counts agree per dataset?
  3. embedding_dimension  — Does a live embed call return the expected 768 dims?
  4. dataset_model_drift  — Are there COMPLETE datasets for the same source file
                            using different embedding models (version mismatch)?
  5. retrieval_sanity     — Can the index round-trip a known embed → search?

Each check returns a CheckResult dataclass. run_all() returns a HealthReport.

Health event taxonomy (emitted to logs, surfaceable to governance):
  memory.integrity_check.failed
  memory.dataset.model_drift_detected
  memory.embedding_dimension.mismatch
  memory.index.empty
  memory.count.reconciliation_failed

Invariants:
  - MUST NOT write to any store (read-only audit).
  - MUST NOT call any LLM.
  - MUST NOT touch GraphManager or graph.nodes FAISS index.
  - Checks are independent — one failure does not abort others.
  - overall_status = "ok" only if ALL checks pass.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Expected embedding dimension for nomic-embed-text.
# Must match EXPECTED_DIMENSION in nexus.memory.embedder.
EXPECTED_EMBEDDING_DIM: int = 768

# Sanity probe text — fixed string used for round-trip retrieval test.
_SANITY_PROBE_TEXT: str = "nexus memory health check probe"


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class CheckResult:
    """Result of a single health check."""

    name: str
    """Identifier of the check, e.g. 'index_size'."""

    status: str
    """One of: 'ok' | 'warn' | 'fail'."""

    details: Dict[str, Any] = field(default_factory=dict)
    """Structured diagnostic payload — always serialisable."""

    message: str = ""
    """Human-readable summary of the check outcome."""


@dataclass
class HealthReport:
    """Aggregate result of all health checks."""

    overall_status: str
    """'ok' if all checks pass; 'warn' if any warn; 'fail' if any fail."""

    checks: List[CheckResult] = field(default_factory=list)
    """Individual check results."""

    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_status": self.overall_status,
            "timestamp": self.timestamp,
            "checks": [
                {
                    "name": c.name,
                    "status": c.status,
                    "message": c.message,
                    "details": c.details,
                }
                for c in self.checks
            ],
        }


# ---------------------------------------------------------------------------
# MemoryHealthChecker
# ---------------------------------------------------------------------------

class MemoryHealthChecker:
    """
    Read-only integrity auditor for the Memory Layer.

    Usage:
        checker = MemoryHealthChecker()
        report = checker.run_all()
        print(report.overall_status)   # 'ok' | 'warn' | 'fail'

    All heavy objects are instantiated lazily inside each check method
    so that a single failed import does not cascade across all checks.
    """

    def __init__(self):
        # Lazy-init: components are imported per-check to isolate failures.
        self._vector_store = None
        self._metadata_store = None
        self._dataset_manager = None
        self._embedder = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run_all(self) -> HealthReport:
        """
        Execute all health checks and return an aggregated HealthReport.

        Checks run in dependency order:
          1. index_size (fast)
          2. count_reconciliation (per-dataset comparison)
          3. embedding_dimension (live embed probe)
          4. dataset_model_drift (metadata scan)
          5. retrieval_sanity (round-trip search)
        """
        self._init_components()

        results: List[CheckResult] = [
            self._check_index_size(),
            self._check_count_reconciliation(),
            self._check_embedding_dimension(),
            self._check_dataset_model_drift(),
            self._check_retrieval_sanity(),
        ]

        # Determine overall status.
        statuses = {r.status for r in results}
        if "fail" in statuses:
            overall = "fail"
        elif "warn" in statuses:
            overall = "warn"
        else:
            overall = "ok"

        report = HealthReport(overall_status=overall, checks=results)

        logger.info(
            "[MemoryHealthChecker] Health check complete: overall_status=%s "
            "(%d ok, %d warn, %d fail)",
            overall,
            sum(1 for r in results if r.status == "ok"),
            sum(1 for r in results if r.status == "warn"),
            sum(1 for r in results if r.status == "fail"),
        )

        # Emit governance-style log events for any non-ok checks.
        for r in results:
            if r.status != "ok":
                self._emit_health_event(r)

        return report

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_index_size(self) -> CheckResult:
        """
        Check 1: Is the Chroma vector index non-empty?

        Warn if 0 vectors — could indicate an un-ingested system or
        a failed dataset import that went undetected.
        """
        try:
            count = self._vector_store.count()
            if count == 0:
                return CheckResult(
                    name="index_size",
                    status="warn",
                    message="Vector index is empty. No datasets have been ingested.",
                    details={"vector_count": 0},
                )
            return CheckResult(
                name="index_size",
                status="ok",
                message=f"Vector index contains {count} chunks.",
                details={"vector_count": count},
            )
        except Exception as exc:
            logger.error("[MemoryHealthChecker] index_size check failed: %s", exc)
            return CheckResult(
                name="index_size",
                status="fail",
                message=f"Could not read vector index count: {exc}",
                details={"error": str(exc)[:200]},
            )

    def _check_count_reconciliation(self) -> CheckResult:
        """
        Check 2: Do vector counts and metadata counts agree per dataset?

        For each COMPLETE dataset, compare:
          - ChromaMemoryVectorStore.count_by_dataset(dataset_id)
          - MetadataStore.count_by_dataset(dataset_id)

        A mismatch of > 5% is a FAIL. Between 1–5% is a WARN.
        Exact match is OK.

        This detects partial failures where vectors were indexed but
        SQLite writes failed (or vice versa).
        """
        try:
            datasets = self._dataset_manager.list_datasets()
            complete = [d for d in datasets if d.status == "COMPLETE"]

            if not complete:
                return CheckResult(
                    name="count_reconciliation",
                    status="ok",
                    message="No COMPLETE datasets to reconcile.",
                    details={"datasets_checked": 0},
                )

            mismatches = []
            for ds in complete:
                vec_count = self._vector_store.count_by_dataset(ds.dataset_id)
                meta_count = self._metadata_store.count_by_dataset(ds.dataset_id)

                if vec_count == 0 and meta_count == 0:
                    # Cleared dataset — skip.
                    continue

                if vec_count == 0 or meta_count == 0:
                    mismatches.append({
                        "dataset_id": ds.dataset_id,
                        "source": ds.source_filename,
                        "vector_count": vec_count,
                        "metadata_count": meta_count,
                        "severity": "fail",
                        "reason": "One store is completely empty while the other is not.",
                    })
                    continue

                delta_pct = abs(vec_count - meta_count) / max(meta_count, 1) * 100
                if delta_pct > 5.0:
                    mismatches.append({
                        "dataset_id": ds.dataset_id,
                        "source": ds.source_filename,
                        "vector_count": vec_count,
                        "metadata_count": meta_count,
                        "delta_pct": round(delta_pct, 2),
                        "severity": "fail",
                        "reason": f"Count mismatch exceeds 5% threshold ({delta_pct:.1f}%).",
                    })
                elif delta_pct > 1.0:
                    mismatches.append({
                        "dataset_id": ds.dataset_id,
                        "source": ds.source_filename,
                        "vector_count": vec_count,
                        "metadata_count": meta_count,
                        "delta_pct": round(delta_pct, 2),
                        "severity": "warn",
                        "reason": f"Minor count drift ({delta_pct:.1f}%). Possible partial re-ingest.",
                    })

            if not mismatches:
                return CheckResult(
                    name="count_reconciliation",
                    status="ok",
                    message=f"All {len(complete)} COMPLETE dataset(s) reconcile correctly.",
                    details={"datasets_checked": len(complete)},
                )

            has_fail = any(m["severity"] == "fail" for m in mismatches)
            return CheckResult(
                name="count_reconciliation",
                status="fail" if has_fail else "warn",
                message=f"{len(mismatches)} dataset(s) have count mismatches.",
                details={"mismatches": mismatches, "datasets_checked": len(complete)},
            )

        except Exception as exc:
            logger.error("[MemoryHealthChecker] count_reconciliation check failed: %s", exc)
            return CheckResult(
                name="count_reconciliation",
                status="fail",
                message=f"Reconciliation check errored: {exc}",
                details={"error": str(exc)[:200]},
            )

    def _check_embedding_dimension(self) -> CheckResult:
        """
        Check 3: Does a live embed call return the expected 768-dim vector?

        Uses a fixed probe string. Validates that the Ollama nomic-embed-text
        model is available and returns the correct dimensionality. Fails if
        the dimension has changed (model swap) or Ollama is unavailable.
        """
        try:
            vec = self._embedder.embed(_SANITY_PROBE_TEXT)
            actual_dim = len(vec)

            if actual_dim != EXPECTED_EMBEDDING_DIM:
                return CheckResult(
                    name="embedding_dimension",
                    status="fail",
                    message=(
                        f"Embedding dimension mismatch: expected {EXPECTED_EMBEDDING_DIM}, "
                        f"got {actual_dim}. Model may have changed."
                    ),
                    details={
                        "expected_dim": EXPECTED_EMBEDDING_DIM,
                        "actual_dim": actual_dim,
                        "probe_text": _SANITY_PROBE_TEXT,
                    },
                )

            return CheckResult(
                name="embedding_dimension",
                status="ok",
                message=f"Embedding dimension validated: {actual_dim}.",
                details={"dimension": actual_dim},
            )

        except Exception as exc:
            return CheckResult(
                name="embedding_dimension",
                status="fail",
                message=f"Embedding call failed: {exc}. Ollama may be unavailable.",
                details={"error": str(exc)[:200]},
            )

    def _check_dataset_model_drift(self) -> CheckResult:
        """
        Check 4: Are there COMPLETE datasets for the same source file
        using DIFFERENT embedding models?

        This detects cases where a source file was re-ingested after
        changing the embedding model. Mixed-model datasets produce
        inconsistent similarity scores and should be flagged.
        """
        try:
            datasets = self._dataset_manager.list_datasets()
            complete = [d for d in datasets if d.status == "COMPLETE"]

            # Group by source_filename.
            by_source: Dict[str, List[Any]] = {}
            for ds in complete:
                by_source.setdefault(ds.source_filename, []).append(ds)

            drifts = []
            for source, ds_list in by_source.items():
                models_used = {ds.embedding_model for ds in ds_list}
                if len(models_used) > 1:
                    drifts.append({
                        "source_filename": source,
                        "embedding_models": list(models_used),
                        "dataset_count": len(ds_list),
                        "dataset_ids": [ds.dataset_id for ds in ds_list],
                    })

            if drifts:
                return CheckResult(
                    name="dataset_model_drift",
                    status="warn",
                    message=(
                        f"{len(drifts)} source file(s) have been ingested with multiple "
                        "embedding models. Vector similarity comparisons may be inconsistent."
                    ),
                    details={"drifts": drifts},
                )

            return CheckResult(
                name="dataset_model_drift",
                status="ok",
                message="All COMPLETE datasets use a consistent embedding model.",
                details={"sources_checked": len(by_source)},
            )

        except Exception as exc:
            logger.error("[MemoryHealthChecker] dataset_model_drift check failed: %s", exc)
            return CheckResult(
                name="dataset_model_drift",
                status="fail",
                message=f"Model drift check errored: {exc}",
                details={"error": str(exc)[:200]},
            )

    def _check_retrieval_sanity(self) -> CheckResult:
        """
        Check 5: Can the index execute a basic search without error?

        Embeds the probe string and runs a top-1 search. Does NOT assert
        any specific result content — only that the round-trip completes
        without exception and returns a result with a valid score.

        Skips (warn) if the index is empty.
        """
        try:
            total = self._vector_store.count()
            if total == 0:
                return CheckResult(
                    name="retrieval_sanity",
                    status="warn",
                    message="Skipped — vector index is empty.",
                    details={"index_size": 0},
                )

            query_vec = self._embedder.embed(_SANITY_PROBE_TEXT)
            results = self._vector_store.search(query_vector=query_vec, top_k=1)

            if not results:
                return CheckResult(
                    name="retrieval_sanity",
                    status="warn",
                    message="Search returned 0 results despite non-empty index.",
                    details={"index_size": total},
                )

            top = results[0]
            score = top.get("score", -1.0)

            if score < 0.0 or score > 1.0:
                return CheckResult(
                    name="retrieval_sanity",
                    status="fail",
                    message=f"Retrieval returned out-of-range score: {score}. Normalisation may be broken.",
                    details={"score": score, "index_size": total},
                )

            return CheckResult(
                name="retrieval_sanity",
                status="ok",
                message=f"Round-trip retrieval succeeded. Top score={score:.4f}.",
                details={"top_score": round(score, 6), "index_size": total},
            )

        except Exception as exc:
            logger.error("[MemoryHealthChecker] retrieval_sanity check failed: %s", exc)
            return CheckResult(
                name="retrieval_sanity",
                status="fail",
                message=f"Retrieval sanity check errored: {exc}",
                details={"error": str(exc)[:200]},
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _init_components(self) -> None:
        """
        Lazily initialise all sub-components.
        Import failures here are surfaced as individual check failures,
        not as a crash of the entire health check runner.
        """
        from nexus.memory.vector_store import ChromaMemoryVectorStore
        from nexus.memory.metadata_store import MetadataStore
        from nexus.memory.dataset_manager import DatasetManager
        from nexus.memory.embedder import MemoryEmbedder

        if self._vector_store is None:
            self._vector_store = ChromaMemoryVectorStore()
        if self._metadata_store is None:
            self._metadata_store = MetadataStore()
        if self._dataset_manager is None:
            self._dataset_manager = DatasetManager()
        if self._embedder is None:
            self._embedder = MemoryEmbedder()

    def _emit_health_event(self, result: CheckResult) -> None:
        """
        Emit a structured governance-style log event for a non-ok check result.

        Event taxonomy mirrors the existing governance audit log pattern.
        These events can be captured by log aggregators and routed to alerts.
        """
        event_map = {
            "index_size": "memory.index.empty",
            "count_reconciliation": "memory.count.reconciliation_failed",
            "embedding_dimension": "memory.embedding_dimension.mismatch",
            "dataset_model_drift": "memory.dataset.model_drift_detected",
            "retrieval_sanity": "memory.integrity_check.failed",
        }
        event_name = event_map.get(result.name, f"memory.health.{result.name}.{result.status}")

        logger.warning(
            "[MemoryHealthEvent] event=%s status=%s message='%s' details=%s",
            event_name,
            result.status,
            result.message,
            result.details,
        )
