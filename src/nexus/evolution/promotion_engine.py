"""
promotion_engine.py — Sandbox → Core Promotion Engine
======================================================
Handles the human-governed workflow for promoting sandbox evolution into Core.

GOVERNANCE INVARIANTS:
  - Sandbox NEVER directly mutates Core
  - Old concept chains are archived (not deleted) — history is immutable
  - All promotions are atomic transactions (rollback on failure)
  - Conflict detection runs before any write
  - Human selects resolution strategy (REPLACE / BRANCH / NEW_CONCEPT / MANUAL)
"""

import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum

from nexus.db import get_adapter


class ConflictSeverity(str, Enum):
    NONE = "NONE"
    LOW = "LOW"       # Only leaf differences
    MEDIUM = "MEDIUM" # Mid-chain divergence
    HIGH = "HIGH"     # Root-level divergence


class ResolutionStrategy(str, Enum):
    REPLACE = "REPLACE"           # Archive old chain, insert new
    BRANCH = "BRANCH"             # Keep both as parallel branches
    NEW_CONCEPT = "NEW_CONCEPT"   # Promote sandbox as entirely new root
    MANUAL = "MANUAL"             # User hand-maps edges


@dataclass
class ConflictReport:
    conflict_severity: ConflictSeverity
    core_chain: List[str]
    sandbox_chain: List[str]
    divergence_point: Optional[str]
    details: Dict = field(default_factory=dict)


@dataclass
class PromotionResult:
    success: bool
    promotion_id: Optional[str]
    resolution_strategy: ResolutionStrategy
    archived_node_ids: List[str]
    inserted_node_ids: List[str]
    new_version_number: int
    error: Optional[str] = None


class PromotionEngine:
    """Sandbox → Core Promotion Engine."""

    def __init__(self, db=None):
        self.db = db or get_adapter()

    # --- public API ---

    def analyze_conflict(self, run_id: str, concept_id: str) -> ConflictReport:
        """
        Compare the Core concept chain with the Sandbox chain for the same concept.
        Returns a ConflictReport indicating severity and the divergence point.

        Severity rules:
          NONE   — sandbox chain is a pure extension (no common node differs)
          LOW    — only leaf nodes differ
          MEDIUM — mid-chain divergence
          HIGH   — root-level or complete replacement
        """
        core_chain = self._get_core_chain(concept_id)
        sandbox_chain = self._get_sandbox_chain(run_id, concept_id)

        if not core_chain:
            # No existing Core chain — no conflict
            return ConflictReport(
                conflict_severity=ConflictSeverity.NONE,
                core_chain=[],
                sandbox_chain=sandbox_chain,
                divergence_point=None,
                details={"reason": "no_core_chain"},
            )

        if not sandbox_chain:
            return ConflictReport(
                conflict_severity=ConflictSeverity.NONE,
                core_chain=core_chain,
                sandbox_chain=[],
                divergence_point=None,
                details={"reason": "empty_sandbox_chain"},
            )

        # Find first point of divergence
        divergence_idx = None
        for i, (c, s) in enumerate(zip(core_chain, sandbox_chain)):
            if c != s:
                divergence_idx = i
                break

        if divergence_idx is None:
            # Chains share a common prefix
            if len(sandbox_chain) > len(core_chain):
                severity = ConflictSeverity.LOW   # sandbox is an extension
            else:
                severity = ConflictSeverity.NONE  # sandbox is a subset
            divergence_point = None
        elif divergence_idx == 0:
            severity = ConflictSeverity.HIGH
            divergence_point = core_chain[0]
        elif divergence_idx <= len(core_chain) // 2:
            severity = ConflictSeverity.MEDIUM
            divergence_point = core_chain[divergence_idx]
        else:
            severity = ConflictSeverity.LOW
            divergence_point = core_chain[divergence_idx]

        return ConflictReport(
            conflict_severity=severity,
            core_chain=core_chain,
            sandbox_chain=sandbox_chain,
            divergence_point=divergence_point,
            details={
                "core_length": len(core_chain),
                "sandbox_length": len(sandbox_chain),
                "divergence_index": divergence_idx,
            },
        )

    def promote(
        self, run_id: str, concept_id: str,
        strategy: ResolutionStrategy, actor: str,
        change_reason: str = ""
    ) -> PromotionResult:
        """
        Atomic promotion of a sandbox evolution chain into Core.

        Strategy effects:
          REPLACE      — Archive old Core chain, insert sandbox chain as new active chain.
                         Records version in graph.concept_versions.
          BRANCH       — Keep existing Core chain, insert sandbox as a parallel branch
                         under the same concept root (branch_id set).
          NEW_CONCEPT  — Sandbox root becomes an independent new concept root in Core.
                         No linkage to the original concept_id.
          MANUAL       — Records the promotion intent but applies no structural changes.
                         Returns success=True so UI can proceed with hand-mapping.

        INVARIANT: If the transaction fails at any point, no Core data is modified.
        """
        promotion_id = str(uuid.uuid4())
        archived_ids: List[str] = []
        inserted_ids: List[str] = []

        try:
            with self.db.transaction() as cur:
                # 1. Fetch current Core version number for this concept
                cur.execute(
                    "SELECT COALESCE(MAX(version_number), 0) FROM graph.concept_versions WHERE concept_id = %s",
                    (concept_id,)
                )
                current_version = cur.fetchone()[0]
                new_version = current_version + 1

                # 2. Fetch sandbox nodes for this concept/run
                cur.execute(
                    """
                    SELECT id, type, data, original_node_id
                    FROM graph_sandbox.nodes
                    WHERE sandbox_run_id = %s
                    ORDER BY created_at ASC
                    """,
                    (run_id,)
                )
                sandbox_nodes = cur.fetchall()

                # 3. Fetch sandbox edges for this run
                cur.execute(
                    """
                    SELECT source_id, target_id, edge_type, metadata
                    FROM graph_sandbox.edges
                    WHERE sandbox_run_id = %s
                    """,
                    (run_id,)
                )
                sandbox_edges = cur.fetchall()

                if strategy == ResolutionStrategy.REPLACE:
                    archived_ids = self._apply_replace(
                        cur, concept_id, sandbox_nodes, sandbox_edges,
                        actor, inserted_ids
                    )

                elif strategy == ResolutionStrategy.BRANCH:
                    branch_id = str(uuid.uuid4())
                    self._apply_branch(
                        cur, concept_id, branch_id,
                        sandbox_nodes, sandbox_edges, actor, inserted_ids
                    )

                elif strategy == ResolutionStrategy.NEW_CONCEPT:
                    self._apply_new_concept(
                        cur, sandbox_nodes, sandbox_edges, actor, inserted_ids
                    )

                elif strategy == ResolutionStrategy.MANUAL:
                    # Record intent only — no structural change
                    pass

                # 4. Record version in concept_versions (for all non-MANUAL strategies)
                if strategy != ResolutionStrategy.MANUAL:
                    cur.execute(
                        """
                        INSERT INTO graph.concept_versions
                            (concept_id, version_number, root_node_id, previous_root_id,
                             change_reason, change_type, promoted_from, promoted_by,
                             archived_chain, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        """,
                        (
                            concept_id,
                            new_version,
                            inserted_ids[0] if inserted_ids else concept_id,
                            concept_id,
                            change_reason or f"Sandbox promotion via {strategy.value}",
                            strategy.value,
                            "sandbox",
                            actor,
                            json.dumps(archived_ids),
                        )
                    )

                # 5. Mark sandbox run as promoted
                cur.execute(
                    "UPDATE graph_sandbox.runs SET status = 'promoted', completed_at = NOW() WHERE id = %s",
                    (run_id,)
                )

                # 6. Mark promotion record as resolved
                cur.execute(
                    """
                    INSERT INTO graph_sandbox.promotions
                        (run_id, conflict_severity, resolution_strategy, resolution_applied,
                         resolved_by, resolved_at)
                    VALUES (%s, %s, %s, TRUE, %s, NOW())
                    ON CONFLICT DO NOTHING
                    """,
                    (run_id, ConflictSeverity.NONE.value, strategy.value, actor)
                )

            return PromotionResult(
                success=True,
                promotion_id=promotion_id,
                resolution_strategy=strategy,
                archived_node_ids=archived_ids,
                inserted_node_ids=inserted_ids,
                new_version_number=new_version,
            )

        except Exception as exc:
            print(f"[PromotionEngine] Promotion failed (run={run_id}): {exc}")
            return PromotionResult(
                success=False,
                promotion_id=None,
                resolution_strategy=strategy,
                archived_node_ids=[],
                inserted_node_ids=[],
                new_version_number=0,
                error=str(exc),
            )

    def discard_sandbox(self, run_id: str, actor: str) -> bool:
        """Mark a sandbox run as discarded. Does not touch Core."""
        try:
            self.db.execute(
                "UPDATE graph_sandbox.runs SET status = 'discarded', completed_at = NOW() WHERE id = %s",
                (run_id,)
            )
            print(f"[PromotionEngine] Sandbox run {run_id} discarded by {actor}.")
            return True
        except Exception as exc:
            print(f"[PromotionEngine] Failed to discard run {run_id}: {exc}")
            return False

    # ------------------------------------------------------------------
    # Strategy implementations
    # ------------------------------------------------------------------

    def _apply_replace(self, cur, concept_id: str, sandbox_nodes, sandbox_edges,
                       actor: str, inserted_ids: List[str]) -> List[str]:
        """
        REPLACE: Archive existing Core chain, insert sandbox chain.
        Returns list of archived node IDs.
        """
        # Archive all active Core nodes in this concept chain
        archived_ids = self._archive_core_chain(cur, concept_id)

        # Copy sandbox nodes into Core graph.nodes
        for sn in sandbox_nodes:
            s_id, s_type, s_data, original_id = sn
            core_id = original_id if original_id else s_id
            data = s_data if isinstance(s_data, dict) else json.loads(s_data or "{}")
            data["promoted_from_sandbox"] = True
            data["promoted_by"] = actor
            data["promoted_at"] = datetime.now(timezone.utc).isoformat()

            cur.execute(
                """
                INSERT INTO graph.nodes (id, type, data, created_at, archived, author_id)
                VALUES (%s, %s, %s, NOW(), FALSE, %s)
                ON CONFLICT (id) DO UPDATE
                    SET data = EXCLUDED.data,
                        archived = FALSE,
                        archived_at = NULL
                """,
                (core_id, s_type, json.dumps(data), actor)
            )
            inserted_ids.append(core_id)

        # Copy sandbox edges into Core graph.edges
        for se in sandbox_edges:
            src, tgt, etype, emeta = se
            src_core = src
            tgt_core = tgt
            meta = emeta if isinstance(emeta, dict) else json.loads(emeta or "{}")
            meta["promoted_from_sandbox"] = True

            cur.execute(
                """
                INSERT INTO graph.edges (source_id, target_id, edge_type, metadata, created_at, archived)
                VALUES (%s, %s, %s, %s, NOW(), FALSE)
                ON CONFLICT DO NOTHING
                """,
                (src_core, tgt_core, etype, json.dumps(meta))
            )

        return archived_ids

    def _apply_branch(self, cur, concept_id: str, branch_id: str,
                      sandbox_nodes, sandbox_edges, actor: str, inserted_ids: List[str]):
        """
        BRANCH: Insert sandbox chain as a parallel branch. Core chain untouched.
        Nodes get branch_id set.
        """
        for sn in sandbox_nodes:
            s_id, s_type, s_data, original_id = sn
            # Branch nodes get a new ID to avoid collision with Core originals
            core_id = f"branch_{branch_id[:8]}_{s_id}"
            data = s_data if isinstance(s_data, dict) else json.loads(s_data or "{}")
            data["branch_id"] = branch_id
            data["promoted_from_sandbox"] = True
            data["promoted_by"] = actor

            cur.execute(
                """
                INSERT INTO graph.nodes (id, type, data, created_at, archived, branch_id, author_id)
                VALUES (%s, %s, %s, NOW(), FALSE, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (core_id, s_type, json.dumps(data), branch_id, actor)
            )
            inserted_ids.append(core_id)

        # Re-map sandbox edges to use new branch node IDs
        id_map = {sn[0]: f"branch_{branch_id[:8]}_{sn[0]}" for sn in sandbox_nodes}
        for se in sandbox_edges:
            src, tgt, etype, emeta = se
            mapped_src = id_map.get(src, src)
            mapped_tgt = id_map.get(tgt, tgt)
            meta = emeta if isinstance(emeta, dict) else json.loads(emeta or "{}")
            meta["branch_id"] = branch_id

            cur.execute(
                """
                INSERT INTO graph.edges (source_id, target_id, edge_type, metadata, created_at, archived)
                VALUES (%s, %s, %s, %s, NOW(), FALSE)
                ON CONFLICT DO NOTHING
                """,
                (mapped_src, mapped_tgt, etype, json.dumps(meta))
            )

    def _apply_new_concept(self, cur, sandbox_nodes, sandbox_edges,
                           actor: str, inserted_ids: List[str]):
        """
        NEW_CONCEPT: Sandbox root becomes entirely new concept root. No link to original.
        """
        for sn in sandbox_nodes:
            s_id, s_type, s_data, _ = sn
            data = s_data if isinstance(s_data, dict) else json.loads(s_data or "{}")
            data["is_new_concept"] = True
            data["promoted_from_sandbox"] = True
            data["promoted_by"] = actor

            cur.execute(
                """
                INSERT INTO graph.nodes (id, type, data, created_at, archived, author_id)
                VALUES (%s, %s, %s, NOW(), FALSE, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (s_id, s_type, json.dumps(data), actor)
            )
            inserted_ids.append(s_id)

        for se in sandbox_edges:
            src, tgt, etype, emeta = se
            meta = emeta if isinstance(emeta, dict) else json.loads(emeta or "{}")
            cur.execute(
                """
                INSERT INTO graph.edges (source_id, target_id, edge_type, metadata, created_at, archived)
                VALUES (%s, %s, %s, %s, NOW(), FALSE)
                ON CONFLICT DO NOTHING
                """,
                (src, tgt, etype, json.dumps(meta))
            )

    def _archive_core_chain(self, cur, concept_id: str) -> List[str]:
        """
        Archive all nodes in the active Core supersession chain starting at concept_id.
        Returns the list of archived node IDs.
        INVARIANT: Sets archived=TRUE and archived_at=NOW(). Never deletes.
        """
        # Recursive CTE to get full chain
        cur.execute(
            """
            WITH RECURSIVE chain(node_id) AS (
                SELECT %s::TEXT
                UNION ALL
                SELECT e.target_id
                FROM graph.edges e
                JOIN chain c ON e.source_id = c.node_id
                WHERE e.edge_type = 'superseded_by' AND e.archived = FALSE
            )
            SELECT node_id FROM chain
            """,
            (concept_id,)
        )
        chain_nodes = [r[0] for r in cur.fetchall()]

        if chain_nodes:
            cur.execute(
                "UPDATE graph.nodes SET archived = TRUE, archived_at = NOW() WHERE id = ANY(%s)",
                (chain_nodes,)
            )
            cur.execute(
                "UPDATE graph.edges SET archived = TRUE, archived_at = NOW() WHERE source_id = ANY(%s)",
                (chain_nodes,)
            )

        return chain_nodes

    # ------------------------------------------------------------------
    # Chain query helpers
    # ------------------------------------------------------------------

    def _get_core_chain(self, concept_id: str) -> List[str]:
        """Returns ordered list of node IDs in active Core supersession chain."""
        rows = self._fetch_all(
            """
            WITH RECURSIVE chain(node_id, depth) AS (
                SELECT %s::TEXT, 0
                UNION ALL
                SELECT e.target_id, c.depth + 1
                FROM graph.edges e
                JOIN chain c ON e.source_id = c.node_id
                WHERE e.edge_type = 'superseded_by' AND e.archived = FALSE
            )
            SELECT node_id FROM chain ORDER BY depth ASC
            """,
            (concept_id,)
        )
        return [r[0] for r in rows]

    def _get_sandbox_chain(self, run_id: str, concept_id: str) -> List[str]:
        """Returns ordered list of node IDs in sandbox supersession chain."""
        # Find the sandbox node corresponding to the concept root
        root_row = self._fetch_one(
            "SELECT id FROM graph_sandbox.nodes WHERE sandbox_run_id = %s AND original_node_id = %s",
            (run_id, concept_id)
        )
        if not root_row:
            # Fallback: take first node in sandbox run
            root_row = self._fetch_one(
                "SELECT id FROM graph_sandbox.nodes WHERE sandbox_run_id = %s ORDER BY created_at ASC LIMIT 1",
                (run_id,)
            )
        if not root_row:
            return []

        sandbox_root = root_row[0]
        rows = self._fetch_all(
            """
            WITH RECURSIVE chain(node_id, depth) AS (
                SELECT %s::TEXT, 0
                UNION ALL
                SELECT e.target_id, c.depth + 1
                FROM graph_sandbox.edges e
                JOIN chain c ON e.source_id = c.node_id
                WHERE e.edge_type = 'superseded_by' AND e.sandbox_run_id = %s
            )
            SELECT node_id FROM chain ORDER BY depth ASC
            """,
            (sandbox_root, run_id)
        )
        return [r[0] for r in rows]

    # --- helpers ---
    def _fetch_one(self, sql, params=None):
        return self.db.fetch_one(sql, params)

    def _fetch_all(self, sql, params=None):
        return self.db.fetch_all(sql, params)
