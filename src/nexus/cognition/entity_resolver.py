"""
Entity Resolver — Nexus Cognitive Operating System v1.0
========================================================

PURPOSE
-------
Prevent semantic duplication and pronoun drift during intent creation.
Runs AFTER Brick extraction and BEFORE GraphManager.register_node().

INVARIANTS
----------
* Never auto-supersedes FROZEN nodes.
* Never mutates existing node content.
* Attaches a Brick to an existing Intent when confidence is HIGH.
* Creates a PROVISIONAL Intent otherwise.
* Flags conflicts for human review.
* All writes (if any) go through GraphManager — never raw SQL.

RESOLUTION ORDER
----------------
1. Exact title match among FROZEN nodes in the target scope.
2. Alias match via cognition.entity_aliases.
3. Embedding similarity search (VectorStore).
4. Scope compatibility check on the winning candidate.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Literal

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------
_HIGH_CONFIDENCE_THRESHOLD = 0.88   # attach_existing
_LOW_CONFIDENCE_THRESHOLD  = 0.55   # below this → create_new
# Between LOW and HIGH → flag_conflict


@dataclass
class ResolutionResult:
    """
    Outcome of EntityResolver.resolve().

    action:
        attach_existing — confidence is high; caller should reuse target_node_id.
        create_new      — no match found; caller should create a new node.
        flag_conflict   — ambiguous match; a human must decide.

    target_node_id:
        The existing FROZEN node ID (attach_existing / flag_conflict paths).
        None on create_new.

    confidence:
        Float in [0.0, 1.0]. Highest similarity score found.

    match_reason:
        Human-readable description of how the match was found.
    """
    action: Literal["attach_existing", "create_new", "flag_conflict"]
    target_node_id: Optional[str]
    confidence: float
    match_reason: str = ""
    candidates: List[Dict[str, Any]] = field(default_factory=list)


class EntityResolver:
    """
    Resolve a candidate entity text against the live FROZEN node graph.

    Parameters
    ----------
    db :
        A PostgresAdapter (from nexus.db).  Injected for testability.
    vector_store :
        A VectorStore instance.  Optional — if unavailable the resolver
        falls back to exact + alias matching only.
    embedder :
        A VectorEmbedder instance.  Required only when vector_store is set.
    """

    def __init__(self, db=None, vector_store=None, embedder=None):
        if db is None:
            from nexus.db import get_adapter
            db = get_adapter()
        self.db = db

        self._vector_store = vector_store
        self._embedder = embedder

        # Lazy-initialise vector components if not supplied.
        if self._vector_store is None or self._embedder is None:
            try:
                from nexus.vector.vector_store import VectorStore
                from nexus.vector.embedder import VectorEmbedder
                self._vector_store = VectorStore()
                self._embedder = VectorEmbedder()
            except Exception as e:
                print(f"[EntityResolver] Vector layer unavailable (non-fatal): {e}")
                self._vector_store = None
                self._embedder = None

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def resolve(self, candidate_text: str, scope_id: str) -> ResolutionResult:
        """
        Attempt to resolve *candidate_text* against existing FROZEN nodes
        that belong to *scope_id*.

        Parameters
        ----------
        candidate_text :
            Raw text of the new candidate intent / concept.
        scope_id :
            The topic / scope this entity should belong to.

        Returns
        -------
        ResolutionResult
        """
        if not candidate_text or not candidate_text.strip():
            return ResolutionResult(
                action="create_new",
                target_node_id=None,
                confidence=0.0,
                match_reason="empty candidate text",
            )

        normalized = candidate_text.strip()

        # ── Step 1: Exact title match (FROZEN nodes in scope) ──────────
        exact = self._exact_match(normalized, scope_id)
        if exact:
            node_id, score = exact
            return ResolutionResult(
                action="attach_existing",
                target_node_id=node_id,
                confidence=score,
                match_reason="exact_title_match",
            )

        # ── Step 2: Alias match ─────────────────────────────────────────
        alias = self._alias_match(normalized, scope_id)
        if alias:
            node_id, score = alias
            return ResolutionResult(
                action="attach_existing",
                target_node_id=node_id,
                confidence=score,
                match_reason="alias_match",
            )

        # ── Step 3: Embedding similarity ────────────────────────────────
        if self._vector_store and self._embedder:
            sim_result = self._similarity_match(normalized, scope_id)
            if sim_result:
                node_id, score, candidates = sim_result
                action = self._score_to_action(score)
                return ResolutionResult(
                    action=action,
                    target_node_id=node_id if action != "create_new" else None,
                    confidence=score,
                    match_reason="embedding_similarity",
                    candidates=candidates,
                )

        # ── Step 4: No match found ──────────────────────────────────────
        return ResolutionResult(
            action="create_new",
            target_node_id=None,
            confidence=0.0,
            match_reason="no_match_found",
        )

    def register_alias(self, node_id: str, alias_text: str) -> bool:
        """
        Register an alias for an existing FROZEN node.
        Idempotent (ON CONFLICT DO NOTHING).

        Returns True on success.
        """
        try:
            self.db.execute(
                """
                INSERT INTO cognition.entity_aliases (node_id, alias_text)
                VALUES (%s, %s)
                ON CONFLICT (node_id, alias_text) DO NOTHING
                """,
                (node_id, alias_text.strip()),
            )
            return True
        except Exception as e:
            print(f"[EntityResolver] register_alias failed: {e}")
            return False

    def get_aliases(self, node_id: str) -> List[str]:
        """Return all registered aliases for a node."""
        rows = self.db.fetch_all(
            "SELECT alias_text FROM cognition.entity_aliases WHERE node_id = %s",
            (node_id,),
        )
        return [r[0] for r in rows]

    # ------------------------------------------------------------------
    # PRIVATE HELPERS
    # ------------------------------------------------------------------

    def _exact_match(
        self, text: str, scope_id: str
    ) -> Optional[tuple[str, float]]:
        """
        Case-insensitive exact match of the 'statement' field among FROZEN
        nodes associated with *scope_id*.
        """
        try:
            rows = self.db.fetch_all(
                """
                SELECT n.id
                FROM graph.nodes n
                JOIN graph.edges e
                    ON n.id = e.source_id
                    AND e.edge_type = 'APPLIES_TO'
                    AND e.target_id = %s
                WHERE n.type IN ('intent', 'concept')
                  AND (n.data->>'lifecycle') = 'frozen'
                  AND LOWER(n.data->>'statement') = LOWER(%s)
                LIMIT 1
                """,
                (scope_id, text),
            )
            if rows:
                return (rows[0][0], 1.0)
        except Exception as e:
            print(f"[EntityResolver] _exact_match error: {e}")
        return None

    def _alias_match(
        self, text: str, scope_id: str
    ) -> Optional[tuple[str, float]]:
        """
        Match against registered aliases.
        Only returns matches for FROZEN nodes.
        """
        try:
            rows = self.db.fetch_all(
                """
                SELECT ea.node_id
                FROM cognition.entity_aliases ea
                JOIN graph.nodes n ON n.id = ea.node_id
                JOIN graph.edges e
                    ON n.id = e.source_id
                    AND e.edge_type = 'APPLIES_TO'
                    AND e.target_id = %s
                WHERE (n.data->>'lifecycle') = 'frozen'
                  AND LOWER(ea.alias_text) = LOWER(%s)
                LIMIT 1
                """,
                (scope_id, text),
            )
            if rows:
                return (rows[0][0], 0.97)
        except Exception as e:
            print(f"[EntityResolver] _alias_match error: {e}")
        return None

    def _similarity_match(
        self, text: str, scope_id: str
    ) -> Optional[tuple[str, float, List[Dict]]]:
        """
        Embed *text* and find the closest FROZEN node via FAISS.
        Filters results to the given *scope_id* using a post-query JOIN.
        Returns (best_node_id, best_score, all_candidates) or None.
        """
        try:
            raw = self._embedder.embed_query(text)
            query_vec = raw.flatten()

            # Oversample to absorb scope-filter losses
            candidates_raw = self._vector_store.search(query_vec, k=20)
            if not candidates_raw:
                return None

            # Build a score map
            id_score: Dict[str, float] = {nid: sc for nid, sc in candidates_raw}
            candidate_ids = list(id_score.keys())

            # Filter: must be FROZEN and in the target scope
            rows = self.db.fetch_all(
                """
                SELECT n.id, n.data->>'statement'
                FROM graph.nodes n
                JOIN graph.edges e
                    ON n.id = e.source_id
                    AND e.edge_type = 'APPLIES_TO'
                    AND e.target_id = %s
                WHERE n.id = ANY(%s)
                  AND n.type IN ('intent', 'concept')
                  AND (n.data->>'lifecycle') = 'frozen'
                """,
                (scope_id, candidate_ids),
            )
            if not rows:
                return None

            # Normalise cosine sim [-1,1] → [0,1]
            scored = sorted(
                [
                    {
                        "node_id": r[0],
                        "statement": r[1],
                        "score": (float(id_score.get(r[0], -1.0)) + 1.0) / 2.0,
                    }
                    for r in rows
                ],
                key=lambda x: x["score"],
                reverse=True,
            )
            best = scored[0]
            return (best["node_id"], best["score"], scored)

        except Exception as e:
            print(f"[EntityResolver] _similarity_match error: {e}")
            return None

    @staticmethod
    def _score_to_action(
        score: float,
    ) -> Literal["attach_existing", "create_new", "flag_conflict"]:
        if score >= _HIGH_CONFIDENCE_THRESHOLD:
            return "attach_existing"
        if score < _LOW_CONFIDENCE_THRESHOLD:
            return "create_new"
        return "flag_conflict"

    # ------------------------------------------------------------------
    # UTILITY — pronoun / coreference normalisation
    # ------------------------------------------------------------------

    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Lightweight text normalization for pre-matching.
        Strips possessives, extra whitespace, and lowercases.
        NOT used for embedding — only for exact/alias comparisons.
        """
        text = text.strip().lower()
        text = re.sub(r"'s\b", "", text)
        text = re.sub(r"\s+", " ", text)
        return text
