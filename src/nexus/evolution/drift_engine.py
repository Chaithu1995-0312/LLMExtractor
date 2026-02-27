import json
from datetime import datetime, timezone
from typing import List, Dict, Optional
import numpy as np

from nexus.db import get_adapter
from nexus.vector.embedding_service import EmbeddingService
from nexus.vector.vector_store import VectorStore

class EvolutionIntegrityError(Exception):
    """Raised when an evolutionary graph mutation violates structural invariants."""
    pass

class DriftEngine:
    """
    Core engine for detecting semantic drift and proposing evolutionary edges.
    Operates in isolation (Phase 1).
    """
    def __init__(self, db=None):
        self.db = db or get_adapter()
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore()

    def process_node(self, node_id: str):
        """
        Main entry point for drift processing. Idempotent.

        Phase 2 contract:
        - This method NO LONGER performs indexing.
        - Indexing is the exclusive responsibility of the `index_node` task
          (services/cortex/tasks.py → process_index_task).
        - This method REQUIRES vector_status='indexed' before proceeding.
          If the node is still pending, it logs and returns. The node will
          be re-processed once index_node completes and schedules process_drift.

        Legacy migration bridge:
        - Pre-Phase-2 nodes may have been indexed inline by a previous version
          of this method. They will have vector_status='indexed' in their data
          and will pass the guard below without any issue.
        - Phase-1 nodes with no vector_status field in data are treated as
          'pending' (see _fetch_node require_indexed=True logic) and will be
          skipped until a backfill or re-index is triggered.

        D-01 invariant preserved:
        - We never touch the vector store here. Drift logic only reads it
          (via vector_store.search). All writes are owned by index_node.
        """
        # 1. Phase 2 Guard: Only process fully-indexed nodes.
        # _fetch_node with require_indexed=True (default) enforces:
        #   data->>'vector_status' = 'indexed'
        # If the node is pending or missing, return early.
        node_data = self._fetch_node(node_id, require_indexed=True)
        if not node_data:
            # Could be: not found, still pending, or superseded (filtered by SQL)
            # Check if the node exists at all for better logging.
            raw = self._fetch_node(node_id, require_indexed=False)
            if raw is None:
                print(f"[DriftEngine] Node {node_id} not found. Skipping.")
            else:
                vs = raw.get("vector_status", "pending")
                lc = raw.get("lifecycle", "unknown")
                print(f"[DriftEngine] Node {node_id} not ready for drift "
                      f"(vector_status={vs}, lifecycle={lc}). Skipping.")
            return

        # Lifecycle Guard: Skip superseded nodes (belt-and-suspenders —
        # _fetch_node already excludes them via require_indexed, but we keep
        # this explicit check for clarity and future schema changes).
        if node_data.get("lifecycle") == "superseded":
            print(f"[DriftEngine] Node {node_id} is SUPERSEDED. Skipping.")
            return

        statement = node_data.get("statement")
        if not statement:
            print(f"[DriftEngine] Node {node_id} has no statement. Skipping.")
            return

        # 2. Fetch the pre-built vector from VectorStore.
        # The vector was created and saved by index_node. We do NOT re-embed here.
        if not self.vector_store.exists(node_id):
            # This should not happen if vector_status='indexed', but guard anyway.
            # Signal clearly so ops can investigate the inconsistency.
            print(f"[DriftEngine] WARN: Node {node_id} has vector_status=indexed "
                  f"but is missing from VectorStore. State inconsistency detected. "
                  f"Skipping drift until re-index completes.")
            return

        vector = self.vector_store.get_vector(node_id)
        if vector is None:
            print(f"[DriftEngine] WARN: vector_store.get_vector({node_id}) returned None. "
                  f"Skipping drift.")
            return

        # 3. Search Similar Nodes — k=10 candidates
        candidates = self.vector_store.search(vector, k=10)

        # 4. Classify & Generate Candidates
        for target_id, score in candidates:
            if target_id == node_id:
                continue

            # Guard: Skip if target is already superseded
            target_data = self._fetch_node(target_id)
            if target_data and target_data.get("lifecycle") == "superseded":
                # D-01: Superseded nodes must also be removed from the vector
                # index to prevent them from resurfacing as drift candidates.
                # Mark for removal in vector_meta; actual index rebuild is a
                # maintenance task (scripts/maintenance/rebuild_vector_index.py).
                self._mark_vector_stale(target_id)
                continue

            relation = self._classify_relationship(score, node_data, target_id)
            if relation:
                # Real Edge Deduplication Guard
                if self._edge_exists(node_id, target_id, relation):
                    continue

                self._store_edge_candidate(node_id, target_id, relation, score)

    def _execute(self, sql, params=None):
        """Helper to handle both adapter and cursor-like db objects."""
        if hasattr(self.db, 'execute'):
            return self.db.execute(sql, params)
        return self.db.execute(sql, params)

    def _fetch_one(self, sql, params=None):
        if hasattr(self.db, 'fetchone'):
            self.db.execute(sql, params)
            return self.db.fetchone()
        return self.db.fetch_one(sql, params)

    def _fetch_all(self, sql, params=None):
        if hasattr(self.db, 'fetchall'):
            self.db.execute(sql, params)
            return self.db.fetchall()
        return self.db.fetch_all(sql, params)

    def _edge_exists(self, source_id: str, target_id: str, edge_type: str) -> bool:
        """
        Checks if a real graph edge already exists.
        """
        row = self._fetch_one(
            "SELECT 1 FROM graph.edges WHERE source_id = %s AND target_id = %s AND edge_type = %s",
            (source_id, target_id, edge_type)
        )
        return row is not None

    def _fetch_node(self, node_id: str, require_indexed: bool = True) -> Optional[Dict]:
        """
        FZ-02: Fetch a node. By default, ONLY returns fully vector-indexed nodes.

        vector_status = 'indexed' means:
          1. The node exists in graph.nodes  ✓
          2. vector_store.add() succeeded    ✓
          3. vector_store.save() completed   ✓
          4. graph.vector_meta was recorded  ✓

        A node with vector_status = 'pending' (or no vector_status field,
        which defaults to 'pending' via the column default) is NOT yet safe
        to include in drift candidate searches. Including it would create a
        ghost drift relationship against an un-indexed node, violating the
        Graph visibility == Vector visibility invariant.

        Setting require_indexed=False is only permitted for the indexer itself
        (process_node) to break the circular dependency.
        """
        sql = "SELECT data FROM graph.nodes WHERE id = %s AND archived = FALSE"
        if require_indexed:
            sql += " AND data->>'vector_status' = 'indexed'"

        row = self._fetch_one(sql, (node_id,))
        if row:
            return row[0] if isinstance(row[0], dict) else json.loads(row[0])
        return None

    def _mark_vector_stale(self, node_id: str):
        """
        D-01 FIX: Mark a node's vector index entry as stale when the node is
        superseded. This prevents superseded nodes from continuing to surface
        in similarity searches and generating ghost drift candidates.

        The actual removal from the in-memory FAISS index requires a full
        index rebuild (FAISS IndexFlatIP does not support deletion). The stale
        flag in graph.vector_meta signals that scripts/maintenance/
        rebuild_vector_index.py should exclude this node on next rebuild.
        """
        try:
            self._execute(
                """
                UPDATE graph.vector_meta
                SET is_stale = TRUE,
                    stale_reason = 'lifecycle:superseded',
                    stale_at = NOW()
                WHERE node_id = %s
                """,
                (node_id,)
            )
            print(f"[DriftEngine] Marked vector entry stale for superseded node {node_id}")
        except Exception as e:
            # Non-fatal: stale marking is a best-effort correctness hint.
            # The maintenance rebuild will re-derive staleness from lifecycle.
            print(f"[DriftEngine] WARN: Could not mark vector stale for {node_id}: {e}")

    def _classify_relationship(self, score: float, source_node: Dict, target_id: str) -> Optional[str]:
        """
        Rule-based classification v1.
        """
        # Thresholds (Lowered for MiniLM testing)
        SIMILARITY_REFINES = 0.85
        SIMILARITY_SUPERSEDES = 0.75
        
        # print(f"[DriftEngine] Debug: Score {score:.4f} vs {target_id}")

        if score > SIMILARITY_REFINES:
            return "REFINES"
        
        if score > SIMILARITY_SUPERSEDES:
            return "SUPERSEDES"
        
        return None

    def _store_edge_candidate(self, source_id: str, target_id: str, edge_type: str, score: float):
        """
        Persist suggestion.
        """
        try:
            self._execute(
                """
                INSERT INTO graph.edge_candidates 
                (source_intent_id, target_intent_id, suggested_edge_type, similarity_score, drift_score, confidence_score, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'PENDING')
                ON CONFLICT (source_intent_id, target_intent_id, suggested_edge_type) DO NOTHING
                """,
                (source_id, target_id, edge_type, float(score), 1.0 - float(score), 0.8) # Mock confidence
            )
            print(f"[DriftEngine] Proposed {edge_type} {source_id}->{target_id} (score={score:.4f})")
        except Exception as e:
            print(f"[DriftEngine] Error storing candidate: {e}")

    def commit_edge(self, candidate_id: str, actor: str) -> bool:
        """
        Promotes a candidate edge to a real graph edge.
        Handles lifecycle updates if SUPERSEDES.
        Atomic transaction.
        """
        try:
            # 1. Fetch Candidate (Non-transactional read first for safety)
            row = self._fetch_one(
                "SELECT source_intent_id, target_intent_id, suggested_edge_type, status FROM graph.edge_candidates WHERE id = %s",
                (candidate_id,)
            )
            if not row:
                raise ValueError(f"Candidate {candidate_id} not found")
            
            source_id, target_id, edge_type, status = row
            
            if status != 'PENDING':
                raise ValueError(f"Candidate {candidate_id} is already {status}")

            # 2. Structural Hardening (Strict Guard Order)
            
            # Guard 1: Self-loop
            if source_id == target_id:
                raise EvolutionIntegrityError("Self supersession is illegal")

            # Note: We assume external transaction management if self.db is a cursor
            if hasattr(self.db, 'transaction'):
                with self.db.transaction() as cur:
                    self._commit_edge_logic(cur, source_id, target_id, edge_type, candidate_id, actor)
            else:
                # If we're already in a cursor, just execute
                self._commit_edge_logic(self.db, source_id, target_id, edge_type, candidate_id, actor)

            print(f"[DriftEngine] Committed edge {candidate_id} ({source_id}->{target_id})")
            return True

        except Exception as e:
            print(f"[DriftEngine] Failed to commit edge {candidate_id}: {e}")
            return False

    def _commit_edge_logic(self, cur, source_id, target_id, edge_type, candidate_id, actor):
        if edge_type == "SUPERSEDES":
            # Guard 2: Single-Successor (Target not already superseded)
            cur.execute(
                "SELECT source_id FROM graph.edges WHERE target_id = %s AND edge_type = 'SUPERSEDES' LIMIT 1",
                (target_id,)
            )
            existing_successor = cur.fetchone()
            if existing_successor:
                raise EvolutionIntegrityError(f"Target {target_id} is already superseded by {existing_successor[0]}")

            # Guard 3: DAG Guard (Hardened Cycle Detection)
            if self._has_path(cur, target_id, source_id, "SUPERSEDES"):
                raise EvolutionIntegrityError(f"Evolutionary cycle detected: path already exists from {target_id} to {source_id}")

        # Guard 4: Lifecycle Guard (Immutable SUPERSEDED nodes)
        cur.execute(
            "SELECT id FROM graph.nodes WHERE id = ANY(%s) AND data->>'lifecycle' = 'superseded'",
            ([source_id, target_id],)
        )
        bad_nodes = cur.fetchall()
        if bad_nodes:
            node_ids = [r[0] for r in bad_nodes]
            raise EvolutionIntegrityError(f"Mutation rejected: Nodes {node_ids} are already SUPERSEDED")

        # 3. Insert Edge
        cur.execute(
            """
            INSERT INTO graph.edges (source_id, target_id, edge_type, metadata, created_at)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT DO NOTHING
            """,
            (source_id, target_id, edge_type, json.dumps({
                "source": "evolution_engine",
                "approved_by": actor,
                "candidate_id": candidate_id
            }))
        )

        # 3. Update Candidate
        cur.execute(
            "UPDATE graph.edge_candidates SET status = 'APPROVED', reviewed_by = %s, reviewed_at = NOW() WHERE id = %s",
            (actor, candidate_id)
        )

        # 4. Handle SUPERSEDES Lifecycle
        if edge_type == "SUPERSEDES":
            cur.execute("SELECT data FROM graph.nodes WHERE id = %s", (target_id,))
            node_row = cur.fetchone()
            if node_row:
                data = node_row[0] if isinstance(node_row[0], dict) else json.loads(node_row[0])
                data["lifecycle"] = "superseded"
                data["superseded_by"] = source_id
                cur.execute("UPDATE graph.nodes SET data = %s WHERE id = %s", (json.dumps(data), target_id))

    def _has_path(self, cur, start_id: str, end_id: str, edge_type: str) -> bool:
        """
        Recursive CTE to check if a path exists between two nodes for a specific edge type.
        Uses UNION (not UNION ALL) to prevent infinite recursion and duplicate paths.
        """
        query = f"""
            WITH RECURSIVE search_path(id) AS (
                SELECT %s
                UNION
                SELECT e.target_id
                FROM graph.edges e
                JOIN search_path sp ON e.source_id = sp.id
                WHERE e.edge_type = %s
            )
            SELECT 1 FROM search_path WHERE id = %s LIMIT 1
        """
        cur.execute(query, (start_id, edge_type, end_id))
        return cur.fetchone() is not None

    def reject_candidate(self, candidate_id: str, actor: str) -> bool:
        """
        Rejects a candidate edge.
        """
        try:
            self._execute(
                "UPDATE graph.edge_candidates SET status = 'REJECTED', reviewed_by = %s, reviewed_at = NOW() WHERE id = %s",
                (actor, candidate_id)
            )
            return True
        except Exception as e:
            print(f"[DriftEngine] Failed to reject candidate {candidate_id}: {e}")
            return False
