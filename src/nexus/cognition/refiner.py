"""
Safe Refiner — Nexus Cognitive Operating System v1.0
=====================================================

PURPOSE
-------
Detect semantic drift and contradictions in the knowledge graph.
NEVER mutates the graph.  Advisory-only output stored in
cognition.drift_reports.

INVARIANTS
----------
* Never calls GraphManager.supersede_node().
* Never calls GraphManager.kill_node().
* Never calls GraphManager.promote_node_to_frozen().
* Never calls GraphManager.register_node() or register_edge().
* Writes ONLY to cognition.drift_reports (append-only advisory table).
* All reads use direct DB queries to minimise coupling.

DETECTION HEURISTICS (spec §8.4)
---------------------------------
1. embedding_distance_shift  — node embedding diverged from its cluster centroid.
2. contradictory_edge        — two FROZEN nodes in scope have edges that signal
                               mutual contradiction (CONFLICTS_WITH / negation).
3. weakening_claim           — a newer node in scope has overlapping embedding
                               but significantly lower confidence than an older peer.
4. superseded_dependency     — a FROZEN node depends on (DEPENDS_ON edge target)
                               a node that has since been SUPERSEDED.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Severity constants
# ---------------------------------------------------------------------------
_SEV_CRITICAL = 0.9
_SEV_HIGH     = 0.7
_SEV_MEDIUM   = 0.5
_SEV_LOW      = 0.25

# Minimum cosine-similarity delta to flag embedding shift
_EMBEDDING_SHIFT_THRESHOLD = 0.30   # 30-point drop from cluster mean

# Minimum overlap score to flag a weakening claim
_WEAKENING_OVERLAP_THRESHOLD = 0.75


# ---------------------------------------------------------------------------
# Data-classes
# ---------------------------------------------------------------------------

@dataclass
class DriftReport:
    """
    Advisory drift report.  Never triggers an automatic graph mutation.
    """
    node_id: str
    issue_type: str            # One of the heuristic keys
    related_nodes: List[str]
    severity: float            # [0.0, 1.0]
    description: str = ""
    topic_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Refiner
# ---------------------------------------------------------------------------

class Refiner:
    """
    Non-destructive audit engine.

    Parameters
    ----------
    db :
        PostgresAdapter.  Injected for testability.
    vector_store :
        VectorStore.  Optional — similarity heuristics are skipped if absent.
    embedder :
        VectorEmbedder.  Optional.
    """

    def __init__(self, db=None, vector_store=None, embedder=None):
        if db is None:
            from nexus.db import get_adapter
            db = get_adapter()
        self.db = db

        self._vector_store = vector_store
        self._embedder = embedder

        if self._vector_store is None or self._embedder is None:
            try:
                from nexus.vector.vector_store import VectorStore
                from nexus.vector.embedder import VectorEmbedder
                self._vector_store = VectorStore()
                self._embedder = VectorEmbedder()
            except Exception as e:
                print(f"[Refiner] Vector layer unavailable (non-fatal): {e}")
                self._vector_store = None
                self._embedder = None

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def audit_topic(self, topic_id: str) -> List[DriftReport]:
        """
        Run all drift heuristics against a topic.

        Returns a list of DriftReport objects.  Does NOT mutate the graph.
        Persists each report to cognition.drift_reports.

        Parameters
        ----------
        topic_id :
            The graph.nodes.id of the topic node.
        """
        reports: List[DriftReport] = []

        # ── Heuristic 1: superseded dependency check ────────────────────
        reports.extend(self._check_superseded_dependencies(topic_id))

        # ── Heuristic 2: contradictory edges ────────────────────────────
        reports.extend(self._check_contradictory_edges(topic_id))

        # ── Heuristic 3: embedding distance shift (vector layer only) ───
        if self._vector_store and self._embedder:
            reports.extend(self._check_embedding_shift(topic_id))
            reports.extend(self._check_weakening_claims(topic_id))

        # ── Persist all reports ─────────────────────────────────────────
        for r in reports:
            self._persist_report(r)

        print(
            f"[Refiner] audit_topic({topic_id}): "
            f"{len(reports)} report(s) generated."
        )
        return reports

    def get_open_reports(
        self, topic_id: Optional[str] = None, limit: int = 100
    ) -> List[Dict]:
        """
        Fetch unresolved drift reports for a topic (or all topics).
        Returns plain dicts suitable for API serialisation.
        """
        if topic_id:
            rows = self.db.fetch_all(
                """
                SELECT id, topic_id, node_id, issue_type, severity,
                       related_nodes, description, created_at
                FROM cognition.drift_reports
                WHERE resolved = FALSE AND topic_id = %s
                ORDER BY severity DESC, created_at DESC
                LIMIT %s
                """,
                (topic_id, limit),
            )
        else:
            rows = self.db.fetch_all(
                """
                SELECT id, topic_id, node_id, issue_type, severity,
                       related_nodes, description, created_at
                FROM cognition.drift_reports
                WHERE resolved = FALSE
                ORDER BY severity DESC, created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
        return [self._row_to_dict(r) for r in rows]

    def mark_resolved(self, report_id: str, resolved_by: str) -> bool:
        """Mark a drift report as human-resolved.  Advisory only."""
        try:
            self.db.execute(
                """
                UPDATE cognition.drift_reports
                SET resolved = TRUE,
                    resolved_at = NOW(),
                    resolved_by = %s
                WHERE id = %s
                """,
                (resolved_by, report_id),
            )
            return True
        except Exception as e:
            print(f"[Refiner] mark_resolved failed: {e}")
            return False

    # ------------------------------------------------------------------
    # HEURISTIC IMPLEMENTATIONS
    # ------------------------------------------------------------------

    def _check_superseded_dependencies(self, topic_id: str) -> List[DriftReport]:
        """
        Heuristic 4 — dependency superseded.

        Find FROZEN nodes in this topic that have a DEPENDS_ON edge pointing
        to a node whose lifecycle is 'superseded'.
        """
        reports: List[DriftReport] = []
        try:
            rows = self.db.fetch_all(
                """
                SELECT n.id AS source_id,
                       dep.id AS dep_id,
                       dep.data->>'lifecycle' AS dep_lifecycle,
                       dep.data->>'statement' AS dep_statement
                FROM graph.nodes n
                JOIN graph.edges e
                    ON n.id = e.source_id
                    AND e.edge_type = 'DEPENDS_ON'
                JOIN graph.nodes dep ON dep.id = e.target_id
                WHERE (n.data->>'lifecycle') = 'frozen'
                  AND (dep.data->>'lifecycle') = 'superseded'
                  AND (
                    n.data->'metadata'->>'sync_topic_id' = %s
                    OR EXISTS (
                        SELECT 1 FROM graph.edges te
                        WHERE te.target_id = n.id AND te.source_id = %s
                    )
                  )
                """,
                (topic_id, topic_id),
            )
            for r in rows:
                reports.append(DriftReport(
                    node_id=r[0],
                    issue_type="superseded_dependency",
                    related_nodes=[r[1]],
                    severity=_SEV_HIGH,
                    description=(
                        f"Node {r[0]} depends on {r[1]} which is now SUPERSEDED. "
                        f"Dependency text: '{(r[3] or '')[:120]}'"
                    ),
                    topic_id=topic_id,
                    metadata={"dep_lifecycle": r[2]},
                ))
        except Exception as e:
            print(f"[Refiner] _check_superseded_dependencies error: {e}")
        return reports

    def _check_contradictory_edges(self, topic_id: str) -> List[DriftReport]:
        """
        Heuristic 2 — contradictory edges.

        Look for CONFLICTS_WITH edges between FROZEN nodes in this topic.
        """
        reports: List[DriftReport] = []
        try:
            rows = self.db.fetch_all(
                """
                SELECT e.source_id, e.target_id,
                       n1.data->>'statement' AS src_stmt,
                       n2.data->>'statement' AS tgt_stmt
                FROM graph.edges e
                JOIN graph.nodes n1 ON n1.id = e.source_id
                JOIN graph.nodes n2 ON n2.id = e.target_id
                WHERE e.edge_type IN ('CONFLICTS_WITH', 'contradicts')
                  AND (n1.data->>'lifecycle') = 'frozen'
                  AND (n2.data->>'lifecycle') = 'frozen'
                  AND (
                    n1.data->'metadata'->>'sync_topic_id' = %s
                    OR EXISTS (
                        SELECT 1 FROM graph.edges te
                        WHERE te.target_id = n1.id AND te.source_id = %s
                    )
                  )
                """,
                (topic_id, topic_id),
            )
            for r in rows:
                reports.append(DriftReport(
                    node_id=r[0],
                    issue_type="contradictory_edge",
                    related_nodes=[r[1]],
                    severity=_SEV_CRITICAL,
                    description=(
                        f"FROZEN node {r[0]} has a CONFLICTS_WITH edge to FROZEN node {r[1]}. "
                        f"This indicates unresolved semantic contradiction."
                    ),
                    topic_id=topic_id,
                ))
        except Exception as e:
            print(f"[Refiner] _check_contradictory_edges error: {e}")
        return reports

    def _check_embedding_shift(self, topic_id: str) -> List[DriftReport]:
        """
        Heuristic 1 — embedding distance shift.

        Compute the centroid of all FROZEN node embeddings in the topic.
        Flag nodes whose cosine distance from the centroid exceeds
        _EMBEDDING_SHIFT_THRESHOLD.
        """
        import numpy as np
        reports: List[DriftReport] = []
        try:
            # Fetch FROZEN nodes for topic
            rows = self.db.fetch_all(
                """
                SELECT n.id, n.data->>'statement'
                FROM graph.nodes n
                WHERE (n.data->>'lifecycle') = 'frozen'
                  AND (
                    n.data->'metadata'->>'sync_topic_id' = %s
                    OR EXISTS (
                        SELECT 1 FROM graph.edges te
                        WHERE te.target_id = n.id AND te.source_id = %s
                    )
                  )
                  AND n.data->>'statement' IS NOT NULL
                """,
                (topic_id, topic_id),
            )
            if len(rows) < 3:
                # Not enough nodes to compute a meaningful centroid
                return []

            # Embed all nodes — use vector_store lookup first to avoid re-embedding
            vecs = []
            node_ids = []
            for r in rows:
                nid = r[0]
                stmt = r[1] or ""
                if not stmt:
                    continue
                # Try existing vector first
                existing = self._vector_store.get_vector(nid) if hasattr(self._vector_store, "get_vector") else None
                if existing is not None:
                    vecs.append(existing)
                else:
                    try:
                        v = self._embedder.embed_query(stmt).flatten()
                        vecs.append(v)
                    except Exception:
                        continue
                node_ids.append(nid)

            if len(vecs) < 3:
                return []

            matrix = np.stack(vecs, axis=0)
            centroid = matrix.mean(axis=0)
            centroid_norm = centroid / (np.linalg.norm(centroid) + 1e-9)

            for i, nid in enumerate(node_ids):
                v = vecs[i]
                v_norm = v / (np.linalg.norm(v) + 1e-9)
                cosine = float(np.dot(v_norm, centroid_norm))
                # Cosine in [-1,1]; lower → further from centroid
                # Convert to distance: distance = (1 - cosine) / 2 in [0,1]
                distance = (1.0 - cosine) / 2.0
                if distance > _EMBEDDING_SHIFT_THRESHOLD:
                    reports.append(DriftReport(
                        node_id=nid,
                        issue_type="embedding_distance_shift",
                        related_nodes=[],
                        severity=round(min(distance, 1.0), 4),
                        description=(
                            f"Node {nid} is {distance:.3f} cosine-distance units from the "
                            f"topic centroid (threshold={_EMBEDDING_SHIFT_THRESHOLD}). "
                            f"The content may have drifted from the topic's core focus."
                        ),
                        topic_id=topic_id,
                        metadata={"centroid_distance": round(distance, 4)},
                    ))
        except Exception as e:
            print(f"[Refiner] _check_embedding_shift error: {e}")
        return reports

    def _check_weakening_claims(self, topic_id: str) -> List[DriftReport]:
        """
        Heuristic 3 — new nodes weakening old claims.

        Find pairs of FROZEN nodes where the newer node has very high
        embedding similarity to the older one but a lower 'stability_score'
        or explicit 'confidence' metadata field.

        This surfaces cases where a revised claim essentially says the same
        thing with less certainty, which may indicate knowledge regression.
        """
        import numpy as np
        reports: List[DriftReport] = []
        try:
            rows = self.db.fetch_all(
                """
                SELECT n.id, n.data->>'statement',
                       COALESCE((n.data->'metadata'->>'confidence')::FLOAT, 1.0) AS conf,
                       n.created_at
                FROM graph.nodes n
                WHERE (n.data->>'lifecycle') = 'frozen'
                  AND (
                    n.data->'metadata'->>'sync_topic_id' = %s
                    OR EXISTS (
                        SELECT 1 FROM graph.edges te
                        WHERE te.target_id = n.id AND te.source_id = %s
                    )
                  )
                  AND n.data->>'statement' IS NOT NULL
                ORDER BY n.created_at ASC
                """,
                (topic_id, topic_id),
            )
            if len(rows) < 2:
                return []

            # Build (id, statement, confidence, created_at, vector) list
            node_data = []
            for r in rows:
                nid, stmt, conf, created_at = r[0], r[1] or "", float(r[2] or 1.0), r[3]
                existing = (
                    self._vector_store.get_vector(nid)
                    if hasattr(self._vector_store, "get_vector")
                    else None
                )
                if existing is not None:
                    node_data.append((nid, conf, created_at, existing))
                else:
                    try:
                        v = self._embedder.embed_query(stmt).flatten()
                        node_data.append((nid, conf, created_at, v))
                    except Exception:
                        continue

            # Compare newer nodes against older ones
            for i in range(1, len(node_data)):
                n_id, n_conf, n_ca, n_vec = node_data[i]
                for j in range(i):
                    o_id, o_conf, o_ca, o_vec = node_data[j]

                    # Cosine similarity
                    denom = (np.linalg.norm(n_vec) + 1e-9) * (np.linalg.norm(o_vec) + 1e-9)
                    cosine = float(np.dot(n_vec, o_vec) / denom)
                    sim = (cosine + 1.0) / 2.0  # normalise to [0,1]

                    if sim >= _WEAKENING_OVERLAP_THRESHOLD and n_conf < o_conf:
                        conf_drop = round(o_conf - n_conf, 4)
                        reports.append(DriftReport(
                            node_id=n_id,
                            issue_type="weakening_claim",
                            related_nodes=[o_id],
                            severity=round(min(conf_drop + 0.2, 1.0), 4),
                            description=(
                                f"Node {n_id} (newer, confidence={n_conf:.3f}) overlaps "
                                f"strongly with older node {o_id} (confidence={o_conf:.3f}) "
                                f"but has lower certainty. Possible knowledge regression."
                            ),
                            topic_id=topic_id,
                            metadata={
                                "similarity": round(sim, 4),
                                "confidence_drop": conf_drop,
                                "older_node": o_id,
                            },
                        ))

        except Exception as e:
            print(f"[Refiner] _check_weakening_claims error: {e}")
        return reports

    # ------------------------------------------------------------------
    # PERSISTENCE
    # ------------------------------------------------------------------

    def _persist_report(self, report: DriftReport) -> bool:
        """
        Write a DriftReport to cognition.drift_reports.
        Non-fatal on error.
        """
        try:
            self.db.execute(
                """
                INSERT INTO cognition.drift_reports
                    (topic_id, node_id, issue_type, severity, related_nodes, description)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    report.topic_id,
                    report.node_id,
                    report.issue_type,
                    report.severity,
                    json.dumps(report.related_nodes),
                    report.description,
                ),
            )
            return True
        except Exception as e:
            print(f"[Refiner] _persist_report failed: {e}")
            return False

    @staticmethod
    def _row_to_dict(row) -> Dict:
        related = row[5]
        if isinstance(related, str):
            try:
                related = json.loads(related)
            except Exception:
                related = []
        return {
            "id": str(row[0]),
            "topic_id": row[1],
            "node_id": row[2],
            "issue_type": row[3],
            "severity": float(row[4] or 0.0),
            "related_nodes": related or [],
            "description": row[6] or "",
            "created_at": str(row[7]),
        }
