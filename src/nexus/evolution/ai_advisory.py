"""
ai_advisory.py — AI Advisory Layer (Periodic Analysis Engine)
=============================================================

Authority Level: READ-ONLY over Core.
LLM: Allowed to ANALYZE and SUGGEST. Cannot mutate Core.

All suggestions written to graph_ai.suggestions with status='pending'.
Human must approve before anything touches Core.

INVARIANTS:
  - Never writes to graph.nodes or graph.edges
  - Never writes to graph_sandbox.*
  - Only writes to graph_ai.suggestions and graph_ai.analysis_runs
  - Suggestions expire after 7 days if not reviewed
"""

import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

from nexus.db import get_adapter


# ---------------------------------------------------------------------------
# Suggestion type constants
# ---------------------------------------------------------------------------
class SuggestionType:
    MERGE         = "MERGE"           # Two nodes are near-duplicates
    CONSOLIDATE   = "CONSOLIDATE"     # Cluster has too many overlapping nodes
    FLAG_UNSTABLE = "FLAG_UNSTABLE"   # Concept has high supersession velocity
    FLAG_CONFLICT = "FLAG_CONFLICT"   # Nodes have contradicting content
    SUMMARIZE     = "SUMMARIZE"       # Cluster needs a synthetic root summary


class AIAdvisory:
    """
    Periodic analysis engine.
    Runs nightly or hourly (triggered by scheduler / cron).
    Produces suggestions for human review in graph_ai.suggestions.
    """

    # Tuneable thresholds
    INSTABILITY_THRESHOLD = 0.5    # cluster instability_score above this → FLAG_UNSTABLE
    CONFLICT_THRESHOLD    = 3      # more than N contradiction edges → FLAG_CONFLICT
    MERGE_SIMILARITY      = 0.90   # cosine similarity above this → MERGE suggestion
    MIN_CONFIDENCE        = 0.60   # only store suggestions above this confidence

    def __init__(self, db=None):
        self.db = db or get_adapter()

    # ------------------------------------------------------------------
    # Main Entry Point
    # ------------------------------------------------------------------

    def run_analysis(self, period: str = "nightly") -> Dict:
        """
        Run a full advisory analysis cycle.
        Returns summary of suggestions created.
        """
        run_id = str(uuid.uuid4())
        suggestions_created = 0

        try:
            # Open analysis run record
            self.db.execute(
                """
                INSERT INTO graph_ai.analysis_runs (id, period, started_at, status)
                VALUES (%s, %s, NOW(), 'running')
                """,
                (run_id, period)
            )

            # 1. Detect unstable clusters
            suggestions_created += self._flag_unstable_clusters(run_id)

            # 2. Detect conflict hotspots
            suggestions_created += self._flag_conflict_hotspots(run_id)

            # 3. Suggest merges (near-duplicate nodes)
            suggestions_created += self._suggest_merges(run_id)

            # 4. Expire old pending suggestions (> 7 days)
            self._expire_stale_suggestions()

            # Mark run as completed
            self.db.execute(
                """
                UPDATE graph_ai.analysis_runs
                SET status = 'completed', completed_at = NOW(), suggestions_created = %s
                WHERE id = %s
                """,
                (suggestions_created, run_id)
            )

            print(f"[AIAdvisory] Analysis run {run_id} completed. Suggestions: {suggestions_created}")
            return {
                "run_id": run_id,
                "period": period,
                "suggestions_created": suggestions_created,
                "status": "completed",
            }

        except Exception as exc:
            self.db.execute(
                "UPDATE graph_ai.analysis_runs SET status = 'failed', error = %s WHERE id = %s",
                (str(exc)[:500], run_id)
            )
            print(f"[AIAdvisory] Analysis run {run_id} failed: {exc}")
            return {
                "run_id": run_id,
                "period": period,
                "suggestions_created": suggestions_created,
                "status": "failed",
                "error": str(exc),
            }

    # ------------------------------------------------------------------
    # Analysis Routines
    # ------------------------------------------------------------------

    def _flag_unstable_clusters(self, run_id: str) -> int:
        """
        Detect clusters with high instability scores from mv_cluster_health.
        Suggests FLAG_UNSTABLE for human review.
        """
        try:
            rows = self.db.fetch_all(
                """
                SELECT cluster_id, node_count, supersession_count, instability_score
                FROM graph.mv_cluster_health
                WHERE instability_score > %s
                ORDER BY instability_score DESC
                LIMIT 20
                """,
                (self.INSTABILITY_THRESHOLD,)
            )
        except Exception:
            # Materialized view may not exist yet — skip gracefully
            return 0

        count = 0
        for r in rows:
            cluster_id, node_count, supersession_count, instability_score = r
            confidence = min(float(instability_score or 0.0), 1.0)
            if confidence < self.MIN_CONFIDENCE:
                continue

            # Fetch representative node IDs for this cluster
            node_rows = self.db.fetch_all(
                "SELECT id FROM graph.nodes WHERE cluster_id = %s AND archived = FALSE LIMIT 5",
                (cluster_id,)
            )
            node_ids = [nr[0] for nr in node_rows]

            self._store_suggestion(
                run_id=run_id,
                suggestion_type=SuggestionType.FLAG_UNSTABLE,
                source_nodes=node_ids,
                target_nodes=[],
                reasoning=(
                    f"Cluster '{cluster_id}' has instability_score={instability_score:.3f} "
                    f"({supersession_count} supersessions across {node_count} nodes). "
                    f"Consider consolidating competing chains."
                ),
                confidence=confidence,
                period="nightly",
            )
            count += 1

        return count

    def _flag_conflict_hotspots(self, run_id: str) -> int:
        """
        Detect nodes with high CONTRADICTS edge counts.
        Suggests FLAG_CONFLICT for human review.
        """
        try:
            rows = self.db.fetch_all(
                """
                SELECT source_id, COUNT(*) AS conflict_count
                FROM graph.edges
                WHERE edge_type = 'contradicts' AND archived = FALSE
                GROUP BY source_id
                HAVING COUNT(*) > %s
                ORDER BY conflict_count DESC
                LIMIT 20
                """,
                (self.CONFLICT_THRESHOLD,)
            )
        except Exception:
            return 0

        count = 0
        for r in rows:
            source_id, conflict_count = r
            confidence = min(0.5 + (conflict_count / 20.0), 1.0)
            if confidence < self.MIN_CONFIDENCE:
                continue

            # Fetch conflicting target IDs
            target_rows = self.db.fetch_all(
                "SELECT target_id FROM graph.edges WHERE source_id = %s AND edge_type = 'contradicts' AND archived = FALSE LIMIT 10",
                (source_id,)
            )
            target_ids = [tr[0] for tr in target_rows]

            self._store_suggestion(
                run_id=run_id,
                suggestion_type=SuggestionType.FLAG_CONFLICT,
                source_nodes=[source_id],
                target_nodes=target_ids,
                reasoning=(
                    f"Node '{source_id}' has {conflict_count} CONTRADICTS edges. "
                    f"This is a conflict hotspot. Review and resolve contradictions."
                ),
                confidence=confidence,
                period="nightly",
            )
            count += 1

        return count

    def _suggest_merges(self, run_id: str) -> int:
        """
        Detect near-duplicate nodes via graph.edge_candidates with high similarity.
        Suggests MERGE for human review.
        Only looks at PENDING or APPROVED REFINES candidates with very high scores.
        """
        try:
            rows = self.db.fetch_all(
                """
                SELECT source_intent_id, target_intent_id, similarity_score
                FROM graph.edge_candidates
                WHERE similarity_score >= %s
                  AND suggested_edge_type IN ('REFINES', 'SUPERSEDES')
                  AND status = 'PENDING'
                ORDER BY similarity_score DESC
                LIMIT 30
                """,
                (self.MERGE_SIMILARITY,)
            )
        except Exception:
            return 0

        count = 0
        seen_pairs = set()
        for r in rows:
            src, tgt, score = r
            pair_key = tuple(sorted([src, tgt]))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            confidence = min(float(score or 0.0), 1.0)
            if confidence < self.MIN_CONFIDENCE:
                continue

            self._store_suggestion(
                run_id=run_id,
                suggestion_type=SuggestionType.MERGE,
                source_nodes=[src],
                target_nodes=[tgt],
                reasoning=(
                    f"Nodes '{src}' and '{tgt}' have cosine similarity={score:.4f} "
                    f"(threshold={self.MERGE_SIMILARITY}). "
                    f"They may be near-duplicates. Consider merging into a single concept."
                ),
                confidence=confidence,
                period="nightly",
            )
            count += 1

        return count

    # ------------------------------------------------------------------
    # Suggestion Storage
    # ------------------------------------------------------------------

    def _store_suggestion(
        self,
        run_id: str,
        suggestion_type: str,
        source_nodes: List[str],
        target_nodes: List[str],
        reasoning: str,
        confidence: float,
        period: str = "nightly",
    ):
        """Write a suggestion to graph_ai.suggestions (idempotent on reasoning hash)."""
        try:
            self.db.execute(
                """
                INSERT INTO graph_ai.suggestions
                    (id, suggestion_type, source_nodes, target_nodes,
                     reasoning, confidence, analysis_run_id, analysis_period, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pending', NOW())
                """,
                (
                    str(uuid.uuid4()),
                    suggestion_type,
                    source_nodes,
                    target_nodes,
                    reasoning,
                    float(confidence),
                    run_id,
                    period,
                )
            )
        except Exception as exc:
            print(f"[AIAdvisory] Failed to store suggestion: {exc}")

    def _expire_stale_suggestions(self):
        """Mark suggestions older than 7 days as 'expired' if still pending."""
        try:
            self.db.execute(
                """
                UPDATE graph_ai.suggestions
                SET status = 'expired'
                WHERE status = 'pending'
                  AND created_at < NOW() - INTERVAL '7 days'
                """
            )
        except Exception as exc:
            print(f"[AIAdvisory] Failed to expire stale suggestions: {exc}")

    # ------------------------------------------------------------------
    # Suggestion Query API (read-only)
    # ------------------------------------------------------------------

    def get_pending_suggestions(self, limit: int = 50) -> List[Dict]:
        """Fetch pending suggestions for the UI AI Insights tab."""
        try:
            rows = self.db.fetch_all(
                """
                SELECT id, suggestion_type, source_nodes, target_nodes,
                       reasoning, confidence, analysis_period, created_at
                FROM graph_ai.suggestions
                WHERE status = 'pending'
                ORDER BY confidence DESC, created_at DESC
                LIMIT %s
                """,
                (limit,)
            )
            return [
                {
                    "id": str(r[0]),
                    "type": r[1],
                    "source_nodes": r[2] or [],
                    "target_nodes": r[3] or [],
                    "reasoning": r[4],
                    "confidence": float(r[5] or 0.0),
                    "period": r[6],
                    "created_at": r[7].isoformat() if hasattr(r[7], "isoformat") else str(r[7]),
                }
                for r in rows
            ]
        except Exception as exc:
            print(f"[AIAdvisory] Failed to fetch suggestions: {exc}")
            return []

    def approve_suggestion(self, suggestion_id: str, actor: str, notes: str = "") -> bool:
        """Mark a suggestion as approved. Does NOT apply structural changes."""
        try:
            self.db.execute(
                """
                UPDATE graph_ai.suggestions
                SET status = 'approved', reviewed_at = NOW(), reviewed_by = %s, review_notes = %s
                WHERE id = %s AND status = 'pending'
                """,
                (actor, notes, suggestion_id)
            )
            return True
        except Exception as exc:
            print(f"[AIAdvisory] Failed to approve suggestion {suggestion_id}: {exc}")
            return False

    def reject_suggestion(self, suggestion_id: str, actor: str, notes: str = "") -> bool:
        """Mark a suggestion as rejected."""
        try:
            self.db.execute(
                """
                UPDATE graph_ai.suggestions
                SET status = 'rejected', reviewed_at = NOW(), reviewed_by = %s, review_notes = %s
                WHERE id = %s AND status = 'pending'
                """,
                (actor, notes, suggestion_id)
            )
            return True
        except Exception as exc:
            print(f"[AIAdvisory] Failed to reject suggestion {suggestion_id}: {exc}")
            return False

    def get_analysis_runs(self, limit: int = 20) -> List[Dict]:
        """Fetch recent analysis run history."""
        try:
            rows = self.db.fetch_all(
                """
                SELECT id, period, started_at, completed_at, suggestions_created, status, error
                FROM graph_ai.analysis_runs
                ORDER BY started_at DESC
                LIMIT %s
                """,
                (limit,)
            )
            return [
                {
                    "id": str(r[0]),
                    "period": r[1],
                    "started_at": r[2].isoformat() if hasattr(r[2], "isoformat") else str(r[2]),
                    "completed_at": r[3].isoformat() if r[3] and hasattr(r[3], "isoformat") else None,
                    "suggestions_created": r[4],
                    "status": r[5],
                    "error": r[6],
                }
                for r in rows
            ]
        except Exception as exc:
            print(f"[AIAdvisory] Failed to fetch analysis runs: {exc}")
            return []
