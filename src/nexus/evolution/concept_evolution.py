"""
concept_evolution.py — Phase 2: Personal Knowledge Evolution View
=================================================================

Provides:
  - get_concept_roots()       : Find all active concept root nodes
  - get_evolution_chain()     : Recursive supersession chain traversal
  - get_node_detail()         : Full node context with all edge directions
  - get_concept_timeline()    : Archived + active version history
  - compute_stability_score() : 1 / (1 + supersession_count)
  - get_cluster_nodes()       : All nodes in a semantic cluster

INVARIANTS:
  - All queries filter archived = FALSE for active data
  - Archived nodes are readable via get_concept_timeline() (read-only)
  - No text mutation occurs here — L1 is immutable
  - This layer only reads and derives structural metadata
"""

import json
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field, asdict

from nexus.db import get_adapter


# ---------------------------------------------------------------------------
# Data Contracts (canonical JSON shapes for API responses)
# ---------------------------------------------------------------------------

@dataclass
class ConceptVersion:
    version_number: int
    root_node_id: str
    previous_root_id: Optional[str]
    change_type: str           # REPLACE | BRANCH | MERGE | FORK
    promoted_from: Optional[str]
    promoted_by: str
    change_reason: Optional[str]
    archived_chain: List[str]
    created_at: str


@dataclass
class EvolutionNode:
    """One step in a supersession chain."""
    id: str
    text: str
    depth: int                 # 0 = root (oldest), N = latest
    created_at: str
    refines: List[Dict] = field(default_factory=list)
    refined_by: List[Dict] = field(default_factory=list)


@dataclass
class NodeDetail:
    """Full node view with all edge relationships."""
    id: str
    text: str
    created_at: str
    vector_status: str
    archived: bool
    stability_score: float
    cluster_id: Optional[str]
    author_id: str
    refines: List[Dict] = field(default_factory=list)
    refined_by: List[Dict] = field(default_factory=list)
    supersedes: List[Dict] = field(default_factory=list)
    superseded_by: List[Dict] = field(default_factory=list)
    # Extended edge types (Phase 3+)
    agrees_with: List[Dict] = field(default_factory=list)
    contradicts: List[Dict] = field(default_factory=list)
    extends: List[Dict] = field(default_factory=list)


@dataclass
class ConceptChain:
    """Full evolution chain for a concept root."""
    concept_id: str
    concept_text: str
    stability_score: float
    supersession_depth: int
    versions: List[EvolutionNode] = field(default_factory=list)


@dataclass
class ConceptRoot:
    """Lightweight concept root summary."""
    concept_id: str
    statement: str
    created_at: str
    cluster_id: Optional[str]
    author_id: str
    stability_score: float


# ---------------------------------------------------------------------------
# ConceptEvolutionAPI
# ---------------------------------------------------------------------------

class ConceptEvolutionAPI:
    """
    Query layer for the Phase 2 Personal Knowledge Evolution View.

    All queries enforce:
      - archived = FALSE for active data reads
      - No writes to Core (read-only layer)
      - Deterministic results (no LLM, no randomness)
    """

    def __init__(self, db=None):
        self.db = db or get_adapter()

    # ------------------------------------------------------------------
    # Low-level helpers
    # ------------------------------------------------------------------

    def _fetch_one(self, sql: str, params=None):
        return self.db.fetch_one(sql, params)

    def _fetch_all(self, sql: str, params=None):
        return self.db.fetch_all(sql, params)

    def _safe_str(self, ts) -> str:
        """Convert timestamp to ISO string safely."""
        if ts is None:
            return ""
        if isinstance(ts, str):
            return ts
        if hasattr(ts, "isoformat"):
            return ts.isoformat()
        return str(ts)

    def _node_row_to_text(self, data) -> str:
        """Extract text representation from node data JSONB."""
        if isinstance(data, dict):
            return data.get("statement", data.get("content", ""))
        try:
            d = json.loads(data)
            return d.get("statement", d.get("content", ""))
        except Exception:
            return str(data)

    # ------------------------------------------------------------------
    # 1. Concept Root Discovery
    # ------------------------------------------------------------------

    def get_concept_roots(self, limit: int = 200, cluster_id: Optional[str] = None) -> List[ConceptRoot]:
        """
        Returns all active concept roots.
        A concept root = a non-archived node with NO incoming active 'superseded_by' edge.

        This is the anchor for the evolution timeline.
        """
        sql = """
            SELECT
                n.id,
                n.data,
                n.created_at,
                n.cluster_id,
                n.author_id,
                n.stability_score
            FROM graph.nodes n
            LEFT JOIN graph.edges e
                ON n.id = e.target_id
                AND e.edge_type = 'superseded_by'
                AND e.archived = FALSE
            WHERE e.id IS NULL
              AND n.archived = FALSE
        """
        params: list = []

        if cluster_id:
            sql += " AND n.cluster_id = %s"
            params.append(cluster_id)

        sql += " ORDER BY n.created_at DESC LIMIT %s"
        params.append(limit)

        rows = self._fetch_all(sql, tuple(params))

        roots = []
        for r in rows:
            text = self._node_row_to_text(r[1])
            roots.append(ConceptRoot(
                concept_id=r[0],
                statement=text,
                created_at=self._safe_str(r[2]),
                cluster_id=r[3],
                author_id=r[4] or "system",
                stability_score=float(r[5] or 1.0),
            ))
        return roots

    # ------------------------------------------------------------------
    # 2. Evolution Chain Traversal (Recursive)
    # ------------------------------------------------------------------

    def get_evolution_chain(self, root_id: str) -> Optional[ConceptChain]:
        """
        Recursive CTE traversal of the supersession chain starting at root_id.
        Returns ordered list of nodes from root (oldest) to latest.

        INVARIANT: Only active (non-archived) edges are followed.
        Archived edges belong to historical timeline (see get_concept_timeline).
        """
        # First verify the root exists and is active
        root_row = self._fetch_one(
            "SELECT data, created_at, stability_score FROM graph.nodes WHERE id = %s AND archived = FALSE",
            (root_id,)
        )
        if not root_row:
            return None

        root_text = self._node_row_to_text(root_row[0])
        root_stability = float(root_row[2] or 1.0)

        # Recursive traversal: root → superseded_by → deeper
        sql = """
            WITH RECURSIVE evolution(source_id, target_id, depth) AS (
                -- Anchor: edges out of the root
                SELECT
                    e.source_id,
                    e.target_id,
                    1 AS depth
                FROM graph.edges e
                WHERE e.edge_type = 'superseded_by'
                  AND e.source_id = %s
                  AND e.archived = FALSE

                UNION ALL

                -- Recursive step: follow chain
                SELECT
                    e.source_id,
                    e.target_id,
                    ev.depth + 1
                FROM graph.edges e
                JOIN evolution ev
                    ON e.source_id = ev.target_id
                WHERE e.edge_type = 'superseded_by'
                  AND e.archived = FALSE
            )
            SELECT DISTINCT
                b.id,
                b.data,
                b.created_at,
                ev.depth
            FROM evolution ev
            JOIN graph.nodes b
                ON b.id = ev.source_id
            WHERE b.archived = FALSE
            ORDER BY ev.depth ASC
        """
        chain_rows = self._fetch_all(sql, (root_id,))

        # Build versions list. Root itself is depth 0.
        versions: List[EvolutionNode] = []

        # Add the root node as depth 0
        root_refinements = self._get_refinements(root_id)
        versions.append(EvolutionNode(
            id=root_id,
            text=root_text,
            depth=0,
            created_at=self._safe_str(root_row[1]),
            refines=root_refinements["refines"],
            refined_by=root_refinements["refined_by"],
        ))

        # Add chain nodes
        seen = {root_id}
        for r in chain_rows:
            nid = r[0]
            if nid in seen:
                continue
            seen.add(nid)
            node_text = self._node_row_to_text(r[1])
            refinements = self._get_refinements(nid)
            versions.append(EvolutionNode(
                id=nid,
                text=node_text,
                depth=int(r[3]),
                created_at=self._safe_str(r[2]),
                refines=refinements["refines"],
                refined_by=refinements["refined_by"],
            ))

        return ConceptChain(
            concept_id=root_id,
            concept_text=root_text,
            stability_score=root_stability,
            supersession_depth=len(versions) - 1,
            versions=versions,
        )

    def _get_refinements(self, node_id: str) -> Dict:
        """Helper: Get REFINES outgoing and incoming edges for a node."""
        out_rows = self._fetch_all(
            """
            SELECT e.target_id, b.data, e.metadata
            FROM graph.edges e
            JOIN graph.nodes b ON b.id = e.target_id
            WHERE e.source_id = %s AND e.edge_type = 'refines' AND e.archived = FALSE
              AND b.archived = FALSE
            LIMIT 20
            """,
            (node_id,)
        )
        in_rows = self._fetch_all(
            """
            SELECT e.source_id, b.data, e.metadata
            FROM graph.edges e
            JOIN graph.nodes b ON b.id = e.source_id
            WHERE e.target_id = %s AND e.edge_type = 'refines' AND e.archived = FALSE
              AND b.archived = FALSE
            LIMIT 20
            """,
            (node_id,)
        )

        def _row_to_dict(r):
            return {
                "id": r[0],
                "text": self._node_row_to_text(r[1]),
                "metadata": r[2] if isinstance(r[2], dict) else json.loads(r[2] or "{}"),
            }

        return {
            "refines": [_row_to_dict(r) for r in out_rows],
            "refined_by": [_row_to_dict(r) for r in in_rows],
        }

    # ------------------------------------------------------------------
    # 3. Full Node Detail
    # ------------------------------------------------------------------

    def get_node_detail(self, node_id: str) -> Optional[NodeDetail]:
        """
        Full node view with all edge relationships in both directions.
        Supports: REFINES, SUPERSEDES/SUPERSEDED_BY, AGREES_WITH, CONTRADICTS, EXTENDS
        """
        row = self._fetch_one(
            """
            SELECT data, created_at, vector_status, archived, stability_score, cluster_id, author_id
            FROM graph.nodes
            WHERE id = %s
            """,
            (node_id,)
        )
        if not row:
            return None

        data = row[0] if isinstance(row[0], dict) else json.loads(row[0] or "{}")
        text = data.get("statement", data.get("content", ""))

        def _edges_out(edge_type: str) -> List[Dict]:
            rows = self._fetch_all(
                """
                SELECT e.target_id, b.data, e.metadata, e.similarity_score
                FROM graph.edges e
                JOIN graph.nodes b ON b.id = e.target_id
                WHERE e.source_id = %s AND e.edge_type = %s AND e.archived = FALSE
                LIMIT 50
                """,
                (node_id, edge_type)
            )
            return [
                {
                    "id": r[0],
                    "text": self._node_row_to_text(r[1]),
                    "similarity": float(r[3]) if r[3] is not None else None,
                    "metadata": r[2] if isinstance(r[2], dict) else json.loads(r[2] or "{}"),
                }
                for r in rows
            ]

        def _edges_in(edge_type: str) -> List[Dict]:
            rows = self._fetch_all(
                """
                SELECT e.source_id, b.data, e.metadata, e.similarity_score
                FROM graph.edges e
                JOIN graph.nodes b ON b.id = e.source_id
                WHERE e.target_id = %s AND e.edge_type = %s AND e.archived = FALSE
                LIMIT 50
                """,
                (node_id, edge_type)
            )
            return [
                {
                    "id": r[0],
                    "text": self._node_row_to_text(r[1]),
                    "similarity": float(r[3]) if r[3] is not None else None,
                    "metadata": r[2] if isinstance(r[2], dict) else json.loads(r[2] or "{}"),
                }
                for r in rows
            ]

        return NodeDetail(
            id=node_id,
            text=text,
            created_at=self._safe_str(row[1]),
            vector_status=row[2] or "pending",
            archived=bool(row[3]),
            stability_score=float(row[4] or 1.0),
            cluster_id=row[5],
            author_id=row[6] or "system",
            refines=_edges_out("refines"),
            refined_by=_edges_in("refines"),
            supersedes=_edges_out("superseded_by"),      # outgoing = this supersedes target
            superseded_by=_edges_in("superseded_by"),    # incoming = something superseded this
            agrees_with=_edges_out("agrees_with"),
            contradicts=_edges_out("contradicts"),
            extends=_edges_out("extends"),
        )

    # ------------------------------------------------------------------
    # 4. Concept Timeline (Active + Archived versions)
    # ------------------------------------------------------------------

    def get_concept_timeline(self, concept_id: str) -> Dict:
        """
        Returns the full version history of a concept, including archived chains.
        This is read-only. Archived nodes are preserved history.

        Returns:
          {
            "concept_id": ...,
            "current_version": ...,
            "versions": [...],  # from graph.concept_versions
            "total_versions": ...
          }
        """
        # Get all version records
        version_rows = self._fetch_all(
            """
            SELECT
                version_number, root_node_id, previous_root_id,
                change_type, promoted_from, promoted_by,
                change_reason, archived_chain, created_at
            FROM graph.concept_versions
            WHERE concept_id = %s
            ORDER BY version_number ASC
            """,
            (concept_id,)
        )

        # Also compute the current active chain for this concept
        current_chain = self.get_evolution_chain(concept_id)

        versions = []
        for r in version_rows:
            archived_chain = r[7]
            if isinstance(archived_chain, str):
                try:
                    archived_chain = json.loads(archived_chain)
                except Exception:
                    archived_chain = []

            versions.append(ConceptVersion(
                version_number=r[0],
                root_node_id=r[1],
                previous_root_id=r[2],
                change_type=r[3] or "REPLACE",
                promoted_from=r[4],
                promoted_by=r[5] or "system",
                change_reason=r[6],
                archived_chain=archived_chain or [],
                created_at=self._safe_str(r[8]),
            ))

        return {
            "concept_id": concept_id,
            "current_version": len(versions),
            "current_chain": asdict(current_chain) if current_chain else None,
            "versions": [asdict(v) for v in versions],
            "total_versions": len(versions),
        }

    # ------------------------------------------------------------------
    # 5. Stability Score (deterministic)
    # ------------------------------------------------------------------

    def compute_stability_score(self, node_id: str) -> float:
        """
        stability = 1 / (1 + supersession_count)

        A concept that has never been superseded has score = 1.0 (fully stable).
        A concept superseded 9 times has score = 0.1 (highly volatile).
        """
        row = self._fetch_one(
            """
            SELECT COUNT(*)
            FROM graph.edges
            WHERE source_id = %s
              AND edge_type = 'superseded_by'
              AND archived = FALSE
            """,
            (node_id,)
        )
        count = int(row[0]) if row else 0
        return round(1.0 / (1.0 + count), 4)

    # ------------------------------------------------------------------
    # 6. Cluster Nodes
    # ------------------------------------------------------------------

    def get_cluster_nodes(self, cluster_id: str, include_archived: bool = False) -> Dict:
        """
        Get all nodes in a semantic cluster.
        Default: active only. Pass include_archived=True for historical view.
        """
        sql = """
            SELECT id, data, created_at, stability_score, archived
            FROM graph.nodes
            WHERE cluster_id = %s
        """
        params: list = [cluster_id]

        if not include_archived:
            sql += " AND archived = FALSE"

        sql += " ORDER BY stability_score DESC, created_at ASC"

        rows = self._fetch_all(sql, tuple(params))

        nodes = []
        for r in rows:
            text = self._node_row_to_text(r[1])
            nodes.append({
                "id": r[0],
                "text": text,
                "created_at": self._safe_str(r[2]),
                "stability_score": float(r[3] or 1.0),
                "archived": bool(r[4]),
            })

        return {
            "cluster_id": cluster_id,
            "node_count": len(nodes),
            "nodes": nodes,
        }

    # ------------------------------------------------------------------
    # 7. Live Metrics Summary
    # ------------------------------------------------------------------

    def get_live_metrics(self) -> Dict:
        """
        Reads from materialized views for the Insights dashboard.
        These views must be refreshed via graph.refresh_metrics() after drift runs.
        """
        # Cluster health summary
        cluster_rows = self._fetch_all(
            """
            SELECT cluster_id, node_count, supersession_count,
                   refinement_count, conflict_count, instability_score,
                   last_activity_at
            FROM graph.mv_cluster_health
            ORDER BY instability_score DESC
            LIMIT 50
            """
        )

        # Supersession velocity (last 30 days)
        velocity_rows = self._fetch_all(
            """
            SELECT day, supersession_count, active_count
            FROM graph.mv_supersession_velocity
            ORDER BY day DESC
            LIMIT 30
            """
        )

        # Convergence index (last 12 weeks)
        convergence_rows = self._fetch_all(
            """
            SELECT week, refinement_count, avg_similarity, similarity_stddev
            FROM graph.mv_convergence_index
            ORDER BY week DESC
            LIMIT 12
            """
        )

        # Total concept root count
        root_count_row = self._fetch_one(
            "SELECT COUNT(*) FROM graph.mv_concept_roots"
        )

        return {
            "concept_root_count": int(root_count_row[0]) if root_count_row else 0,
            "cluster_health": [
                {
                    "cluster_id": r[0],
                    "node_count": r[1],
                    "supersession_count": r[2],
                    "refinement_count": r[3],
                    "conflict_count": r[4],
                    "instability_score": float(r[5] or 0.0),
                    "last_activity_at": self._safe_str(r[6]),
                }
                for r in cluster_rows
            ],
            "supersession_velocity": [
                {
                    "day": self._safe_str(r[0]),
                    "supersession_count": r[1],
                    "active_count": r[2],
                }
                for r in velocity_rows
            ],
            "convergence_index": [
                {
                    "week": self._safe_str(r[0]),
                    "refinement_count": r[1],
                    "avg_similarity": float(r[2]) if r[2] is not None else None,
                    "similarity_stddev": float(r[3]) if r[3] is not None else None,
                }
                for r in convergence_rows
            ],
        }

    # ------------------------------------------------------------------
    # 8. Refresh Metrics Views
    # ------------------------------------------------------------------

    def refresh_metrics(self) -> bool:
        """
        Triggers a CONCURRENT refresh of all materialized views.
        Safe to call after bulk drift runs.
        Returns True on success.
        """
        try:
            self.db.execute("SELECT graph.refresh_metrics()")
            return True
        except Exception as e:
            print(f"[ConceptEvolutionAPI] Failed to refresh metrics: {e}")
            return False
