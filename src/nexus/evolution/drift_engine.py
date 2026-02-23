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
    def __init__(self):
        self.db = get_adapter()
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore()

    def process_node(self, node_id: str):
        """
        Main entry point. Idempotent.
        """
        # 1. Fetch Node
        node_data = self._fetch_node(node_id)
        if not node_data:
            print(f"[DriftEngine] Node {node_id} not found. Skipping.")
            return

        # Lifecycle Guard: Skip superseded nodes
        if node_data.get("lifecycle") == "superseded":
            print(f"[DriftEngine] Node {node_id} is SUPERSEDED. Skipping.")
            return

        statement = node_data.get("statement")
        if not statement:
            print(f"[DriftEngine] Node {node_id} has no statement. Skipping.")
            return

        # 2. Embed & Store (Idempotent)
        if not self.vector_store.exists(node_id):
            vector = self.embedding_service.embed(statement)
            self.vector_store.add(node_id, vector)
            self._record_vector_meta(node_id)
            print(f"[DriftEngine] Indexed node {node_id}")
        else:
            # Re-fetch vector for search (VectorStore doesn't expose get_vector yet, so re-embed)
            # Optimization: In Phase 2, VectorStore should support get_vector if feasible, 
            # or we rely on the fact that if it exists, we might still want to search.
            # For now, we re-embed to search. Cost is low for local model.
            vector = self.embedding_service.embed(statement)

        # 3. Search Similar Nodes
        # k=10 candidates
        candidates = self.vector_store.search(vector, k=10)
        
        # 4. Classify & Generate Candidates
        for target_id, score in candidates:
            if target_id == node_id:
                continue
            
            # Guard: Skip if target is already superseded
            target_data = self._fetch_node(target_id)
            if target_data and target_data.get("lifecycle") == "superseded":
                continue

            relation = self._classify_relationship(score, node_data, target_id)
            if relation:
                # Real Edge Deduplication Guard
                if self._edge_exists(node_id, target_id, relation):
                    continue
                
                self._store_edge_candidate(node_id, target_id, relation, score)

    def _edge_exists(self, source_id: str, target_id: str, edge_type: str) -> bool:
        """
        Checks if a real graph edge already exists.
        """
        row = self.db.fetch_one(
            "SELECT 1 FROM graph.edges WHERE source_id = %s AND target_id = %s AND edge_type = %s",
            (source_id, target_id, edge_type)
        )
        return row is not None

    def _fetch_node(self, node_id: str) -> Optional[Dict]:
        row = self.db.fetch_one("SELECT data FROM graph.nodes WHERE id = %s", (node_id,))
        if row:
            return row[0] if isinstance(row[0], dict) else json.loads(row[0])
        return None

    def _record_vector_meta(self, node_id: str):
        """
        Records metadata about the embedding to ensure version consistency.
        """
        self.db.execute(
            """
            INSERT INTO graph.vector_meta (node_id, embedding_model, embedding_version, indexed_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (node_id) DO UPDATE SET
                embedding_model = EXCLUDED.embedding_model,
                embedding_version = EXCLUDED.embedding_version,
                indexed_at = NOW()
            """,
            (node_id, self.embedding_service.model_name, self.embedding_service.model_version())
        )

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
            self.db.execute(
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
            row = self.db.fetch_one(
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

            with self.db.transaction() as cur:
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
                # Ensure neither node is already SUPERSEDED
                # Using ANY(%s) for safe array-based parameter expansion
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
                    # Mark target (older node) as SUPERSEDED
                    # Fetch current data first to update safely
                    cur.execute("SELECT data FROM graph.nodes WHERE id = %s", (target_id,))
                    node_row = cur.fetchone()
                    if node_row:
                        data = node_row[0] if isinstance(node_row[0], dict) else json.loads(node_row[0])
                        data["lifecycle"] = "superseded"
                        data["superseded_by"] = source_id
                        cur.execute("UPDATE graph.nodes SET data = %s WHERE id = %s", (json.dumps(data), target_id))

            print(f"[DriftEngine] Committed edge {candidate_id} ({source_id}->{target_id})")
            return True

        except Exception as e:
            print(f"[DriftEngine] Failed to commit edge {candidate_id}: {e}")
            return False

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
            self.db.execute(
                "UPDATE graph.edge_candidates SET status = 'REJECTED', reviewed_by = %s, reviewed_at = NOW() WHERE id = %s",
                (actor, candidate_id)
            )
            return True
        except Exception as e:
            print(f"[DriftEngine] Failed to reject candidate {candidate_id}: {e}")
            return False
