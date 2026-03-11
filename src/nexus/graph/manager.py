import json
import os
from datetime import datetime, timezone
from threading import Lock
from typing import Dict, Any, Tuple, List, Optional, Union, Generator

import numpy as np

from nexus.graph.schema import (
    Intent, Source, ScopeNode, Edge, EdgeType, IntentLifecycle, 
    IntentType, GraphNode, AuditEventType, ModelTier, DecisionAction
)
from nexus.config import AUDIT_LOG_PATH
from nexus.db import get_adapter
from nexus.db.init_db import init_database

# Node types whose text content should be embedded and indexed in FAISS.
EMBEDDABLE_TYPES = frozenset({"brick", "intent", "concept", "source"})


class GraphManager:
    # Class-level lock so all GraphManager instances share one FAISS write-gate.
    _vector_lock: Lock = Lock()

    def __init__(self, db_path: str = None, db=None):
        # db_path is ignored in Postgres implementation
        # db can be an injected cursor for transactional coupling
        self.db = db or get_adapter()
        if not db:
            self._init_db()
            # Enforce unified storage on startup - Idempotent
            self.sync_bricks_to_nodes()

        # -------------------------------------------------------------------
        # Vector primitive — initialise once, not per call.
        # VectorEmbedder uses a shared class-level model cache so loading
        # the sentence-transformer only happens once per process.
        # -------------------------------------------------------------------
        try:
            from nexus.vector.embedder import VectorEmbedder
            from nexus.vector.vector_store import VectorStore
            self.embedder = VectorEmbedder()
            self.vector_store = VectorStore()
            
            # OPTION B: Hydrate FAISS from Postgres on startup
            self.load_vectors_from_postgres()
            
        except Exception as e:
            print(f"[GraphManager] Vector layer unavailable (non-fatal): {e}")
            self.embedder = None
            self.vector_store = None

        # Pending-write counter used to batch FAISS persistence.
        self._vector_write_counter: int = 0
        self._VECTOR_PERSIST_EVERY: int = 20

    def _init_db(self):
        """Initialize the database with the schema."""
        try:
            init_database()
        except Exception as e:
            print(f"[GraphManager] Error initializing database: {e}")

    def _is_adapter(self):
        # PostgresAdapter has 'pool', sqlite cursor does not. 
        # Also added 'connection' attribute to PostgresAdapter.
        return hasattr(self.db, 'pool') or hasattr(self.db, 'connection')

    def _execute(self, sql, params=None):
        return self.db.execute(sql, params)

    def _fetch_one(self, sql, params=None):
        if self._is_adapter():
            return self.db.fetch_one(sql, params)
        # Cursor path
        self.db.execute(sql, params)
        return self.db.fetchone()

    def _fetch_all(self, sql, params=None):
        if self._is_adapter():
            return self.db.fetch_all(sql, params)
        # Cursor path
        self.db.execute(sql, params)
        return self.db.fetchall()

    def register_node(self, node_type: str, node_id: str, attrs: Dict[str, Any], merge: bool = False):
        """
        Register a generic node. Idempotent by default.
        If merge=True, updates existing node data.

        Two-Phase Commit strategy:
          Phase 1 — DB Transaction: upsert node + insert pulse (ACID).
          Phase 2 — Vector Index:   add to FAISS after DB commit (eventual).

        If the DB commit fails, no vector entry is written.
        If the FAISS write fails, the DB entry is preserved; vector drift
        can be repaired via reindex_all().
        """
        # Pre-compute the embedding BEFORE the transaction.
        # This way, if embedding fails we never enter the DB transaction
        # and the caller gets a clean exception with no partial state.
        #
        # NOTE: Vector updates (merge=True) are NOT supported in-place because
        # IndexFlatIP has no delete/update primitive. If statement text changes,
        # call reindex_all() to rebuild a clean index. Partial overwrite would
        # silently pollute the index with stale duplicate vectors.
        vector = None
        text = attrs.get("statement") or attrs.get("content") or ""
        if node_type in EMBEDDABLE_TYPES and text and self.embedder and self.vector_store:
            # Always embed; VectorStore.add() is idempotent (skips if already indexed).
            # On merge=True with changed text, reindex_all() must be called separately.
            try:
                raw = self.embedder.embed_query(text)
                # embed_query returns shape (1, 384); flatten to (384,)
                vector = raw.flatten()
            except Exception as emb_err:
                # Fail fast: embedding error prevents node creation so index stays clean.
                raise RuntimeError(f"[GraphManager] Embedding failed for {node_id}: {emb_err}") from emb_err

        # root_topic flag
        root_topic = attrs.get("root_topic", False)

        # Phase 1 — DB Transaction (ACID)
        if self._is_adapter():
            with self.db.transaction() as cur:
                self._register_node_logic(cur, node_type, node_id, attrs, merge)
                # Persist pulse inside same transaction.
                self._persist_pulse_in_tx(
                    cur,
                    event_type="node_registered",
                    node_id=node_id,
                    payload={"node_type": node_type, "merge": merge},
                )
        else:
            self._register_node_logic(self.db, node_type, node_id, attrs, merge)

        # Phase 2 — Post-Commit Vector Index (eventual consistency)
        if vector is not None:
            self._commit_vector(node_id, vector)

    def _register_node_logic(self, cur, node_type: str, node_id: str, attrs: Dict[str, Any], merge: bool = False):
        try:
            root_topic = attrs.get("root_topic", False)
            # Check if exists
            cur.execute("SELECT data, root_topic FROM graph.nodes WHERE id = %s", (node_id,))
            row = cur.fetchone()
            
            if row:
                if merge:
                    existing_data = row[0] if isinstance(row[0], dict) else json.loads(row[0])
                    existing_data.update(attrs)
                    cur.execute(
                        "UPDATE graph.nodes SET data = %s, root_topic = %s WHERE id = %s",
                        (json.dumps(existing_data), root_topic, node_id)
                    )
                return # Already exists or updated
            
            # Insert
            cur.execute(
                "INSERT INTO graph.nodes (id, type, data, root_topic, created_at) VALUES (%s, %s, %s, %s, NOW())",
                (node_id, node_type, json.dumps(attrs), root_topic)
            )
        except Exception as e:
            print(f"Error registering node {node_id}: {e}")
            raise

    # ------------------------------------------------------------------
    # VECTOR HELPERS
    # ------------------------------------------------------------------

    def _commit_vector(self, node_id: str, vector: np.ndarray):
        """Thread-safe post-commit write to FAISS. Never raises — errors are logged."""
        try:
            with GraphManager._vector_lock:
                self.vector_store.add(node_id, vector)
                self._vector_write_counter += 1
                if self._vector_write_counter >= self._VECTOR_PERSIST_EVERY:
                    self.vector_store.save()
                    self._vector_write_counter = 0
        except Exception as ve:
            print(f"[GraphManager] ⚠️  Vector write failed for {node_id} (non-fatal): {ve}")
            try:
                self._execute(
                    """
                    INSERT INTO governance.audit_trace (event_type, actor, payload, created_at)
                    VALUES (%s, %s, %s, NOW())
                    """,
                    ("VECTOR_INDEX_FAILED", "GraphManager", json.dumps({"node_id": node_id, "error": str(ve)}))
                )
            except Exception:
                pass  # Audit failure must not disrupt caller

    def load_vectors_from_postgres(self):
        """
        Hydrate the FAISS index from the graph.vector_meta table on startup.
        This bridges the gap between sync_agent (Postgres) and GraphManager (FAISS).
        """
        if not self.vector_store:
            return

        print("[GraphManager] Hydrating FAISS index from Postgres graph.vector_meta...")
        try:
            # Check if table exists
            if self._is_adapter():
                exists = self.db.fetch_one("SELECT to_regclass('graph.vector_meta')")
            else:
                self.db.execute("SELECT to_regclass('graph.vector_meta')")
                exists = self.db.fetchone()
                
            if not exists or not exists[0]:
                print("[GraphManager] graph.vector_meta table not found. Skipping hydration.")
                return

            # Fetch all vectors not in FAISS (optimization: fetch all for now to be safe/simple)
            # vector_meta has: node_id, embedding (vector string/array)
            # Postgres 'vector' type returns as string "[0.1, 0.2, ...]" or list depending on adapter
            
            # MIGRATION: Prefer embedding_v2 (1536) for unification
            query = "SELECT node_id, embedding_v2 FROM graph.vector_meta WHERE embedding_v2 IS NOT NULL"
            
            if self._is_adapter():
                rows = self.db.fetch_all(query)
            else:
                self.db.execute(query)
                rows = self.db.fetchall()

            added_count = 0
            for r in rows:
                node_id = r[0]
                embedding_raw = r[1]
                
                # Parse embedding
                if isinstance(embedding_raw, str):
                    embedding = json.loads(embedding_raw)
                elif isinstance(embedding_raw, list):
                    embedding = embedding_raw
                elif isinstance(embedding_raw, np.ndarray):
                    embedding = embedding_raw.tolist()
                else:
                    continue

                # Add to FAISS if not exists
                if not self.vector_store.exists(node_id):
                    vec_np = np.array(embedding, dtype="float32")
                    try:
                        self.vector_store.add(node_id, vec_np)
                        added_count += 1
                    except Exception as e:
                        print(f"Failed to add vector for {node_id}: {e}")

            if added_count > 0:
                self.vector_store.save()
                print(f"[GraphManager] Hydrated {added_count} vectors from Postgres.")
            else:
                print("[GraphManager] FAISS index up to date with Postgres.")

        except Exception as e:
            print(f"[GraphManager] Failed to hydrate vectors from Postgres: {e}")

    def semantic_query(
        self,
        text: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Hybrid semantic search: vector similarity → SQL join → lifecycle filter → re-rank.

        Args:
            text:    Natural-language query string.
            filters: Optional dict of JSONB field filters, e.g.:
                     {"lifecycle": "frozen", "type": "brick"}
            top_k:   Number of results to return.

        Returns:
            List of node dicts enriched with `vector_score` and `confidence`.
        """
        if not self.embedder or not self.vector_store:
            print("[GraphManager] semantic_query: vector layer not available.")
            return []

        # Step 1 — Embed the query.
        raw = self.embedder.embed_query(text)
        query_vec = raw.flatten()

        # Step 2 — FAISS: oversample to absorb filtering losses.
        oversample = max(top_k * 3, 30)
        candidates = self.vector_store.search(query_vec, k=oversample)
        if not candidates:
            return []

        # Step 3 — Preserve vector scores for re-ranking after SQL.
        id_score_map: Dict[str, float] = {node_id: score for node_id, score in candidates}
        candidate_ids = list(id_score_map.keys())

        # Step 4 — SQL fetch + inline filters.
        #   We use ANY(%s) for the IN clause so psycopg2 can bind a list.
        base_query = "SELECT id, type, data, created_at FROM graph.nodes WHERE id = ANY(%s)"
        params: List[Any] = [candidate_ids]

        type_filter = (filters or {}).get("type")
        lifecycle_filter = (filters or {}).get("lifecycle")

        if type_filter:
            base_query += " AND type = %s"
            params.append(type_filter)
        if lifecycle_filter:
            base_query += " AND data->>'lifecycle' = %s"
            params.append(lifecycle_filter)

        rows = self._fetch_all(base_query, tuple(params))

        # Step 5 — Governance-aware hybrid re-ranking.
        #
        # final_score = base_score × lifecycle_weight × recency_boost
        #
        # base_score:       cosine sim [-1,1] normalised to [0,1] via (s+1)/2
        # lifecycle_weight: governance authority — frozen nodes are more authoritative
        # recency_boost:    slight favour for recently-created nodes (decays over time)
        #
        # This moves retrieval from "most semantically similar" to
        # "most semantically similar AND most authoritative", which is
        # correct behaviour for a governed memory substrate.

        _LIFECYCLE_WEIGHT = {
            "frozen":    1.2,
            "forming":   1.1,
            "loose":     1.0,
            "superseded": 0.6,
            "killed":    0.1,
        }

        now = datetime.now(timezone.utc)
        results = []

        for r in rows:
            node_id = r[0]
            node_type = r[1]
            created_at = r[3]
            data = r[2] if isinstance(r[2], dict) else json.loads(r[2] or "{}")

            cosine = id_score_map.get(node_id, 0.0)

            # Normalise cosine similarity [-1,1] → [0,1]
            base_score = (float(cosine) + 1.0) / 2.0

            lifecycle = data.get("lifecycle", "loose")
            lifecycle_weight = _LIFECYCLE_WEIGHT.get(lifecycle, 1.0)

            # Recency boost: starts at 1.1 for brand-new nodes, decays to 1.0
            # after 10 days, stays at 1.0 thereafter. Handles missing/bad timestamps.
            try:
                if created_at:
                    if hasattr(created_at, "replace"):
                        # psycopg2 returns datetime; ensure UTC-aware
                        ca = created_at.replace(tzinfo=timezone.utc) if created_at.tzinfo is None else created_at
                        days_old = (now - ca).days
                    else:
                        days_old = 999
                else:
                    days_old = 999
            except Exception:
                days_old = 999

            recency_boost = max(1.0, 1.1 - (days_old * 0.01))

            final_score = min(base_score * lifecycle_weight * recency_boost, 2.0)

            results.append({
                "id": node_id,
                "type": node_type,
                "statement": data.get("statement") or data.get("content", ""),
                "lifecycle": lifecycle,
                "created_at": str(created_at),
                "vector_score": round(float(cosine), 6),
                "confidence": round(base_score, 4),
                "final_score": round(final_score, 6),
                "metadata": data.get("metadata", {}),
            })

        results.sort(key=lambda x: x["final_score"], reverse=True)
        return results[:top_k]

    # ------------------------------------------------------------------
    # INDEX MAINTENANCE
    # ------------------------------------------------------------------

    def reindex_all(self, batch_size: int = 100) -> int:
        """
        Rebuild the FAISS index from scratch using all embeddable nodes in the DB.
        Use after model upgrades, corruption, or initial bootstrap.

        Returns the number of nodes indexed.
        """
        if not self.embedder or not self.vector_store:
            print("[GraphManager] reindex_all: vector layer not available.")
            return 0

        import faiss
        print("[GraphManager] reindex_all: clearing and rebuilding vector index …")

        # Fetch all embeddable node types
        type_list = list(EMBEDDABLE_TYPES)
        rows = self._fetch_all(
            "SELECT id, type, data FROM graph.nodes WHERE type = ANY(%s)",
            (type_list,)
        )

        # Rebuild in-memory index
        new_index = faiss.IndexFlatIP(1536) # UPDATED for text-embedding-3-small
        new_id_map: Dict[str, int] = {}
        new_reverse_map: Dict[int, str] = {}
        counter = 0
        skipped = 0

        for r in rows:
            node_id = r[0]
            data = r[2] if isinstance(r[2], dict) else json.loads(r[2] or "{}")
            text = data.get("statement") or data.get("content") or ""
            if not text:
                skipped += 1
                continue
            try:
                vec = self.embedder.embed_query(text).flatten().reshape(1, -1)
                new_index.add(vec)
                new_id_map[node_id] = counter
                new_reverse_map[counter] = node_id
                counter += 1
            except Exception as e:
                print(f"[GraphManager] reindex_all: skip {node_id}: {e}")
                skipped += 1

        # Atomically replace the in-memory index and persist
        with GraphManager._vector_lock:
            self.vector_store.index = new_index
            self.vector_store.id_map = new_id_map
            self.vector_store.reverse_id_map = new_reverse_map
            self.vector_store.next_id = counter
            self.vector_store.save()

        print(f"[GraphManager] reindex_all: indexed {counter} nodes, skipped {skipped}.")
        return counter

    def validate_vector_integrity(self) -> Dict[str, List[str]]:
        """
        Compare DB embeddable nodes vs FAISS index.
        Returns missing_vectors (in DB but not FAISS) and orphaned_vectors
        (in FAISS but not DB) as lists of node IDs.
        """
        if not self.vector_store:
            return {"missing_vectors": [], "orphaned_vectors": [], "error": "vector layer unavailable"}

        type_list = list(EMBEDDABLE_TYPES)
        rows = self._fetch_all(
            "SELECT id FROM graph.nodes WHERE type = ANY(%s)",
            (type_list,)
        )
        db_ids = {r[0] for r in rows}
        index_ids = set(self.vector_store.id_map.keys())

        return {
            "missing_vectors": sorted(db_ids - index_ids),
            "orphaned_vectors": sorted(index_ids - db_ids),
        }

    def get_intents_by_topic(self, topic_node_id: str) -> List[Intent]:
        """
        Retrieve all intents linked to a specific topic.
        """
        query = """
            SELECT n.id, n.data, n.created_at 
            FROM graph.nodes n
            JOIN graph.edges e ON n.id = e.target_id
            WHERE e.source_id = %s AND e.edge_type = %s AND n.type = 'intent'
        """
        rows = self._fetch_all(query, (topic_node_id, EdgeType.ASSEMBLED_IN.value))
        
        intents = []
        for r in rows:
            data = r[1] if isinstance(r[1], dict) else json.loads(r[1])
            i = Intent(
                id=r[0],
                created_at=r[2],
                name=data.get("name", ""),
                summary=data.get("summary", ""),
                lifecycle=IntentLifecycle(data.get("lifecycle", "loose")),
                intent_type=IntentType(data.get("intent_type", "unknown")),
                metadata=data.get("metadata", {})
            )
            intents.append(i)
        return intents

    def _check_for_cycle(self, start_node_id: str, target_node_id: str, edge_type_str: str) -> Optional[List[str]]:
        """
        DFS to detect cycles for a specific edge type.
        Guardrail 1: Type-scoped traversal.
        """
        visited = set()
        
        def dfs(current_id, path):
            if current_id == start_node_id:
                return path + [current_id]
            if current_id in visited:
                return None
            
            visited.add(current_id)
            
            # Fetch outgoing edges of the same type
            rows = self._fetch_all("SELECT target_id FROM graph.edges WHERE source_id=%s AND edge_type=%s", (current_id, edge_type_str))
            targets = [row[0] for row in rows]
            
            for t in targets:
                cycle = dfs(t, path + [current_id])
                if cycle:
                    return cycle
            return None

        # Start DFS from the target of the proposed edge
        return dfs(target_node_id, [])

    def register_edge(self, src: Tuple[str, str], dst: Tuple[str, str], edge_type: Any, attrs: Dict[str, Any] = None):
        """
        Register an edge. Idempotent.
        src = (type, id)
        dst = (type, id)
        """
        src_id = src[1]
        dst_id = dst[1]
        
        # Ensure edge_type is a string (handles Enum)
        edge_type_str = edge_type.value if hasattr(edge_type, 'value') else str(edge_type)
        
        # P0.1 Real-Time Cycle Prevention
        # Only for versioning edges: OVERRIDES and SUPERSEDED_BY
        if edge_type_str in [EdgeType.OVERRIDES.value, EdgeType.SUPERSEDED_BY.value]:
            cycle = self._check_for_cycle(src_id, dst_id, edge_type_str)
            if cycle:
                raise ValueError(f"Cycle detected for {edge_type_str}: {' -> '.join(cycle)}")

        # ── Ontology Acyclicity Guard ──────────────────────────────────
        # IS_SUBTOPIC_OF must not form cycles in the ontology hierarchy.
        if edge_type_str == "IS_SUBTOPIC_OF":
            cycle = self._check_for_cycle(src_id, dst_id, edge_type_str)
            if cycle:
                raise ValueError(
                    f"Ontology cycle detected for IS_SUBTOPIC_OF: {' -> '.join(cycle)}"
                )

        if self._is_adapter():
            with self.db.transaction() as cur:
                self._register_edge_logic(cur, src_id, dst_id, edge_type_str, attrs)
        else: # Cursor
            self._register_edge_logic(self.db, src_id, dst_id, edge_type_str, attrs)

    def _register_edge_logic(self, cur, src_id, dst_id, edge_type_str, attrs):
        try:
            # Check if exists
            cur.execute(
                "SELECT edge_type FROM graph.edges WHERE source_id=%s AND target_id=%s AND edge_type=%s",
                (src_id, dst_id, edge_type_str)
            )
            if cur.fetchone():
                return

            cur.execute(
                "INSERT INTO graph.edges (source_id, target_id, edge_type, metadata, created_at) VALUES (%s, %s, %s, %s, NOW())",
                (src_id, dst_id, edge_type_str, json.dumps(attrs or {}))
            )
        except Exception as e:
            print(f"Error registering edge {src_id}->{dst_id}: {e}")
            raise

    # Typed helpers for new Schema
    def add_intent(self, intent: Intent):
        data = {
            "name": intent.name,
            "summary": intent.summary,
            "lifecycle": intent.lifecycle.value,
            "intent_type": intent.intent_type.value,
            "metadata": intent.metadata
        }
        self.register_node("intent", intent.id, data)

    def add_source(self, source: Source):
        data = {
            "content": source.content,
            "origin_file": source.origin_file,
            "origin_span": source.origin_span,
            "metadata": source.metadata
        }
        self.register_node("source", source.id, data)

    def add_scope(self, scope: ScopeNode):
        data = {
            "name": scope.name,
            "description": scope.description,
            "metadata": scope.metadata
        }
        self.register_node("scope", scope.id, data)

    def _get_node_data(self, node_id: str) -> Optional[Dict]:
        row = self._fetch_one("SELECT data FROM graph.nodes WHERE id=%s", (node_id,))
        if row:
            return row[0] if isinstance(row[0], dict) else json.loads(row[0])
        return None

    def get_node(self, node_id: str) -> Optional[Tuple[str, Dict]]:
        """
        Retrieve node type and data.
        Returns (type, data_dict) or None.
        """
        row = self._fetch_one("SELECT type, data FROM graph.nodes WHERE id=%s", (node_id,))
        if row:
            data = row[1] if isinstance(row[1], dict) else json.loads(row[1])
            return (row[0], data)
        return None

    # ------------------------------------------------------------------
    # PULSE / NARRATIVE LAYER
    # ------------------------------------------------------------------

    def _persist_pulse_in_tx(self, cur, event_type: str, node_id: Optional[str], payload: Dict[str, Any]):
        """
        Persist a pulse inside an ALREADY-OPEN transaction cursor.
        Called from register_node so the pulse is atomic with the node upsert.
        """
        try:
            cur.execute(
                "INSERT INTO graph.pulse_events (event_type, node_id, payload) VALUES (%s, %s, %s)",
                (event_type, node_id, json.dumps(payload)),
            )
        except Exception as e:
            print(f"[GraphManager] pulse_in_tx insert failed (non-fatal): {e}")

    def _emit_pulse(
        self,
        event_type: str,
        payload: Dict[str, Any],
        topic_id: Optional[str] = None,
        severity: str = "info",
        source: str = "GraphManager",
    ):
        """
        Emit a Pulse Envelope — now with durable DB persistence.

        1. Writes to graph.pulse_events (narrative stream).
        2. Prints to stdout (legacy tooling compatibility).
        3. Emits via SocketIO if server is active.
        """
        import uuid
        envelope = {
            "pulse_id": str(uuid.uuid4()),
            "pulse_type": event_type,
            "topic_id": topic_id,
            "severity": severity,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "payload": payload,
        }

        # 1. Persist to DB
        try:
            if self._is_adapter():
                with self.db.transaction() as cur:
                    cur.execute(
                        "INSERT INTO graph.pulse_events (event_type, node_id, payload) VALUES (%s, %s, %s)",
                        (event_type, topic_id, json.dumps(payload)),
                    )
            else:
                self.db.execute(
                    "INSERT INTO graph.pulse_events (event_type, node_id, payload) VALUES (%s, %s, %s)",
                    (event_type, topic_id, json.dumps(payload)),
                )
        except Exception as e:
            print(f"[GraphManager] Pulse persist failed (non-fatal): {e}")

        # 2. Stdout
        try:
            print(f"⚡ [PULSE L1] {json.dumps(envelope)}")
        except Exception:
            pass

        # 3. SocketIO broadcast
        try:
            from services.cortex.server import socketio
            if socketio:
                socketio.emit("pulse_event", envelope)
        except (ImportError, RuntimeError):
            pass

    def get_system_story(
        self,
        limit: int = 50,
        node_id: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return recent pulse events from graph.pulse_events enriched with
        node context. Powers the /jarvis/system-story endpoint.
        """
        query = """
            SELECT
                pe.id::text,
                pe.event_type,
                pe.node_id,
                pe.payload,
                pe.created_at,
                n.type            AS node_type,
                n.data->>'lifecycle' AS lifecycle
            FROM graph.pulse_events pe
            LEFT JOIN graph.nodes n ON n.id = pe.node_id
        """
        conditions: List[str] = []
        params: List[Any] = []

        if node_id:
            conditions.append("pe.node_id = %s")
            params.append(node_id)
        if event_type:
            conditions.append("pe.event_type = %s")
            params.append(event_type)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY pe.created_at DESC LIMIT %s"
        params.append(limit)

        rows = self._fetch_all(query, tuple(params))
        events = []
        for r in rows:
            pld = r[3] if isinstance(r[3], dict) else json.loads(r[3] or "{}")
            events.append({
                "id": r[0],
                "event_type": r[1],
                "node_id": r[2],
                "payload": pld,
                "created_at": str(r[4]),
                "node_type": r[5],
                "lifecycle": r[6],
            })
        return events

    def _log_audit_event(
        self, 
        event_type: Union[AuditEventType, str], 
        agent: str,
        component: str,
        decision_action: DecisionAction,
        reason: str,
        topic_id: Optional[str] = None,
        run_id: Optional[str] = None,
        model_tier: Optional[ModelTier] = None,
        cost_usd: Optional[float] = None,
        tokens_in: Optional[int] = None,
        tokens_out: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log a standardized audit event. Appends to governance.audit_trace.
        """
        ts = datetime.now(timezone.utc).isoformat()
        
        event_str = event_type.value if hasattr(event_type, 'value') else str(event_type)
        
        event = {
            "timestamp": ts,
            "event": event_str,
            "component": component,
            "agent": agent,
            "topic_id": topic_id,
            "run_id": run_id,
            "model_tier": model_tier.value if model_tier else None,
            "cost": {
                "usd": cost_usd or 0.0,
                "tokens_in": tokens_in or 0,
                "tokens_out": tokens_out or 0
            } if model_tier else None,
            "decision": {
                "action": decision_action.value if hasattr(decision_action, 'value') else str(decision_action),
                "reason": reason[:200] # Cap reason length
            },
            "metadata": metadata or {}
        }
        
        # Economic Cognition Invariant: 
        # Any operation that invokes a non-free model must emit cost metadata.
        if model_tier and model_tier != ModelTier.L1 and (cost_usd is None):
            print(f"⚠️ [AUDIT WARNING] Silent spend detected for {event_str}. Model tier {model_tier} requires explicit cost.")

        print(f"[AUDIT] {json.dumps(event)}")
        
        # Append to DB
        try:
            self._execute(
                """
                INSERT INTO governance.audit_trace (event_type, actor, payload, created_at)
                VALUES (%s, %s, %s, NOW())
                """,
                (event_str, agent, json.dumps(event))
            )
        except Exception as e:
            print(f"ERROR: Failed to write to audit log: {e}")

        # Broadcast live event via SocketIO if available
        try:
            from services.cortex.server import socketio
            if socketio:
                socketio.emit("audit_event", event)
        except (ImportError, RuntimeError):
            # Fail silently if socketio is not available or if called outside application context
            pass

    def kill_node(self, node_id: str, reason: str, actor: str):
        """
        Explicitly reject a node, moving it to KILLED lifecycle.
        Preserves history (no delete).
        """
        data = self._get_node_data(node_id)
        if not data:
            raise ValueError(f"Node {node_id} not found")

        current_state = IntentLifecycle(data.get("lifecycle", "loose"))
        if current_state == IntentLifecycle.KILLED:
            # Idempotent success
            return

        # Update node data
        data["lifecycle"] = IntentLifecycle.KILLED.value
        data["kill_reason"] = reason
        data["killed_at"] = datetime.now(timezone.utc).isoformat()
        data["killed_by"] = actor
        
        # Persist
        self._execute("UPDATE graph.nodes SET data=%s WHERE id=%s", (json.dumps(data), node_id))

        # Audit
        self._log_audit_event(
            event_type=AuditEventType.NODE_KILLED,
            agent=actor,
            component="graph",
            decision_action=DecisionAction.REJECTED,
            reason=reason,
            metadata={"node_id": node_id, "previous_state": current_state.value}
        )

        self._emit_pulse("NODE_KILLED", {"id": node_id, "actor": actor, "reason": reason})

    def promote_node_to_frozen(self, node_id: str, promote_bricks: List[str], actor: str):
        """
        Promote a FORMING node to FROZEN.
        Converts specified soft anchors to hard anchors.
        """
        data = self._get_node_data(node_id)
        if not data:
            raise ValueError(f"Node {node_id} not found")

        current_state = IntentLifecycle(data.get("lifecycle", "loose"))
        
        # Validate lifecycle
        if current_state != IntentLifecycle.FORMING:
             raise ValueError(f"Cannot freeze node {node_id}: State is {current_state}, must be FORMING")

        # Logic for anchors would go here. 
        # For now we just update the lifecycle as the brick/anchor model in `data` might vary.
        # Assuming `data` has lists for anchors if we were fully rigorous, but Schema is loose JSON.
        # We will set the lifecycle and log the promotion.
        
        data["lifecycle"] = IntentLifecycle.FROZEN.value
        data["promoted_at"] = datetime.now(timezone.utc).isoformat()
        data["promoted_by"] = actor
        # Store which bricks were the 'reason' for promotion if we want
        data["hard_anchors"] = list(set(data.get("hard_anchors", []) + promote_bricks))

        # Persist
        self._execute("UPDATE graph.nodes SET data=%s WHERE id=%s", (json.dumps(data), node_id))

        self._log_audit_event(
            event_type=AuditEventType.NODE_FROZEN,
            agent=actor,
            component="graph",
            decision_action=DecisionAction.PROMOTED,
            reason="Promotion from FORMING to FROZEN based on anchors",
            metadata={"node_id": node_id, "promoted_bricks": promote_bricks}
        )

        self._emit_pulse("NODE_FROZEN", {"id": node_id, "actor": actor})

    def supersede_node(self, old_node_id: str, new_node_id: str, reason: str, actor: str):
        """
        Declare that one node replaces another.
        Both must be FROZEN.
        """
        old_data = self._get_node_data(old_node_id)
        if not old_data:
             raise ValueError(f"Old node {old_node_id} not found")
        
        new_data = self._get_node_data(new_node_id)
        if not new_data:
             raise ValueError(f"New node {new_node_id} not found")

        # Validate lifecycles
        old_lifecycle = IntentLifecycle(old_data.get("lifecycle", "loose"))
        new_lifecycle = IntentLifecycle(new_data.get("lifecycle", "loose"))

        if old_lifecycle != IntentLifecycle.FROZEN:
            raise ValueError(f"Old node {old_node_id} is not FROZEN ({old_lifecycle})")
        # Strictness: New node should also be FROZEN or being frozen? 
        # Requirement says "Both nodes exist... both lifecycle == FROZEN".
        if new_lifecycle != IntentLifecycle.FROZEN:
            raise ValueError(f"New node {new_node_id} is not FROZEN ({new_lifecycle})")

        if old_node_id == new_node_id:
            raise ValueError("Cannot supersede a node with itself")

        if self._is_adapter():
            with self.db.transaction() as cur:
                self._supersede_node_logic(cur, old_node_id, new_node_id, old_data, new_data, reason, actor)
        else: # Cursor
            self._supersede_node_logic(self.db, old_node_id, new_node_id, old_data, new_data, reason, actor)

    def _supersede_node_logic(self, cur, old_node_id, new_node_id, old_data, new_data, reason, actor):
        # 1. Create Edge
        edge_type_str = EdgeType.SUPERSEDED_BY.value
        cur.execute(
            "INSERT INTO graph.edges (source_id, target_id, edge_type, metadata, created_at) VALUES (%s, %s, %s, %s, NOW()) ON CONFLICT DO NOTHING",
            (old_node_id, new_node_id, edge_type_str, json.dumps({
                "reason": reason,
                "actor": actor,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }))
        )

        # 2. Update Node Metadata (Old)
        old_data["superseded_by"] = new_node_id
        
        # 3. Update Node Metadata (New)
        new_data["supersedes"] = list(set(new_data.get("supersedes", []) + [old_node_id]))

        # Persist Nodes
        cur.execute("UPDATE graph.nodes SET data=%s WHERE id=%s", (json.dumps(old_data), old_node_id))
        cur.execute("UPDATE graph.nodes SET data=%s WHERE id=%s", (json.dumps(new_data), new_node_id))

        self._log_audit_event(
            event_type=AuditEventType.NODE_SUPERSEDED,
            agent=actor,
            component="graph",
            decision_action=DecisionAction.SUPERSEDED,
            reason=reason,
            metadata={"old_node": old_node_id, "new_node": new_node_id}
        )

    def promote_intent(self, intent_id: str, new_lifecycle: IntentLifecycle):
        """
        Promote an intent to a new lifecycle state, enforcing monotonicity and invariants.
        """
        data = self._get_node_data(intent_id)
        if not data:
            raise ValueError(f"Intent {intent_id} not found")
        
        current_state = IntentLifecycle(data.get("lifecycle", "loose"))
        
        # Monotonicity Checks
        # Allow LOOSE -> KILLED directly (quick rejection)
        valid_transitions = {
            IntentLifecycle.LOOSE: [IntentLifecycle.FORMING, IntentLifecycle.KILLED], 
            IntentLifecycle.FORMING: [IntentLifecycle.FROZEN, IntentLifecycle.KILLED],
            IntentLifecycle.FROZEN: [IntentLifecycle.SUPERSEDED, IntentLifecycle.KILLED],
            IntentLifecycle.SUPERSEDED: [IntentLifecycle.KILLED],
            IntentLifecycle.KILLED: []
        }
        
        if new_lifecycle not in valid_transitions.get(current_state, []):
             # Exception: Repromoting same state is no-op
             if new_lifecycle == current_state:
                 return
             raise ValueError(f"Invalid transition: {current_state} -> {new_lifecycle}")

        # Invariant Checks
        if new_lifecycle == IntentLifecycle.FROZEN:
            # Must have APPLIES_TO edge
            edges = self.get_edges_for_node(intent_id)
            has_scope = any(e.edge_type == EdgeType.APPLIES_TO and e.source_id == intent_id for e in edges)
            if not has_scope:
                raise ValueError("Cannot freeze Intent without APPLIES_TO scope edge.")
        
        # Update
        data["lifecycle"] = new_lifecycle.value
        self._execute("UPDATE graph.nodes SET data=%s WHERE id=%s", (json.dumps(data), intent_id))

    def add_typed_edge(self, edge: Edge, actor: str = "system"):
        # Write-Time Invariants
        if edge.edge_type == EdgeType.OVERRIDES:
            # 1. Source must be FROZEN
            src_data = self._get_node_data(edge.source_id)
            if not src_data:
                raise ValueError(f"Source {edge.source_id} not found")
            
            src_lifecycle = IntentLifecycle(src_data.get("lifecycle", "loose"))
            if src_lifecycle != IntentLifecycle.FROZEN:
                 raise ValueError(f"Cannot add OVERRIDES edge from non-FROZEN intent {edge.source_id} ({src_lifecycle})")

            # 2. Target cannot have multiple OVERRIDES
            existing = self._fetch_all("SELECT source_id FROM graph.edges WHERE target_id=%s AND edge_type=%s", (edge.target_id, EdgeType.OVERRIDES.value))
            if existing:
                # If existing is same source, it's idempotent retry, allow.
                if existing[0][0] != edge.source_id:
                    self._log_audit_event(
                        event_type=AuditEventType.EDGE_REJECTED,
                        agent=actor,
                        component="graph",
                        decision_action=DecisionAction.REJECTED,
                        reason=f"Target {edge.target_id} already overridden by {existing[0][0]}",
                        metadata={"edge": str(edge)}
                    )
                    raise ValueError(f"Target {edge.target_id} already overridden by {existing[0][0]}")

        self.register_edge(
            ("node", edge.source_id),
            ("node", edge.target_id),
            edge.edge_type.value,
            edge.metadata
        )

    def get_all_intents(self) -> List[Intent]:
        rows = self._fetch_all("SELECT id, data, created_at FROM graph.nodes WHERE type='intent'")
        
        intents = []
        for r in rows:
            data = r[1] if isinstance(r[1], dict) else json.loads(r[1])
            i = Intent(
                id=r[0],
                created_at=r[2],
                name=data.get("name", ""),
                summary=data.get("summary", ""),
                lifecycle=IntentLifecycle(data.get("lifecycle", "loose")),
                intent_type=IntentType(data.get("intent_type", "unknown")),
                metadata=data.get("metadata", {})
            )
            intents.append(i)
        return intents

    def get_all_edges(self) -> List[Edge]:
        rows = self._fetch_all("SELECT source_id, target_id, edge_type, metadata FROM graph.edges")
        
        edges = []
        for r in rows:
            e = Edge(
                source_id=r[0],
                target_id=r[1],
                edge_type=EdgeType(r[2]),
                metadata=json.loads(r[3] if r[3] else "{}")
            )
            edges.append(e)
        return edges

    def get_edges_for_node(self, node_id: str) -> List[Edge]:
        # Outgoing
        out_rows = self._fetch_all("SELECT source_id, target_id, edge_type, metadata FROM graph.edges WHERE source_id=%s", (node_id,))
        # Incoming
        in_rows = self._fetch_all("SELECT source_id, target_id, edge_type, metadata FROM graph.edges WHERE target_id=%s", (node_id,))
        
        edges = []
        for r in out_rows + in_rows:
            e = Edge(
                source_id=r[0],
                target_id=r[1],
                edge_type=EdgeType(r[2]),
                metadata=json.loads(r[3] if r[3] else "{}")
            )
            edges.append(e)
        return edges

    def get_all_scopes(self) -> Dict[str, ScopeNode]:
        rows = self._fetch_all("SELECT id, data, created_at FROM graph.nodes WHERE type='scope'")
        
        scopes = {}
        for r in rows:
            data = json.loads(r[1])
            s = ScopeNode(
                id=r[0],
                created_at=r[2],
                name=data.get("name", ""),
                description=data.get("description", ""),
                metadata=data.get("metadata", {})
            )
            scopes[r[0]] = s
        return scopes

    def get_root_topics(self) -> List[Dict[str, Any]]:
        """
        Return all nodes marked as root_topic = True, sorted by label.
        """
        rows = self._fetch_all(
            "SELECT id, type, data FROM graph.nodes WHERE root_topic = True"
        )
        topics = []
        for r in rows:
            data = r[2] if isinstance(r[2], dict) else json.loads(r[2] or "{}")
            topics.append({
                "id": r[0],
                "type": r[1],
                "label": data.get("name") or data.get("label") or r[0],
                **data
            })
        return sorted(topics, key=lambda x: x["label"])
    
    def get_all_sources(self) -> Dict[str, Source]:
        rows = self._fetch_all("SELECT id, data, created_at FROM graph.nodes WHERE type='source'")

        sources = {}
        for r in rows:
            data = json.loads(r[1])
            s = Source(
                id=r[0],
                created_at=r[2],
                content=data.get("content", ""),
                origin_file=data.get("origin_file", ""),
                origin_span=data.get("origin_span"),
                metadata=data.get("metadata", {})
            )
            sources[r[0]] = s
        return sources

    def delete_node(self, node_id: str) -> bool:
        """
        Delete a node and all connected edges.
        """
        try:
            if self._is_adapter():
                with self.db.transaction() as cur:
                    self._delete_node_logic(cur, node_id)
            else: # Cursor
                self._delete_node_logic(self.db, node_id)
            return True
        except Exception as e:
            print(f"Error deleting node {node_id}: {e}")
            return False

    def _delete_node_logic(self, cur, node_id):
        # Delete edges where this node is source or target
        cur.execute("DELETE FROM graph.edges WHERE source_id = %s OR target_id = %s", (node_id, node_id))
        # Delete the node
        cur.execute("DELETE FROM graph.nodes WHERE id = %s", (node_id,))

    def get_loose_bricks(self, topic_id: str) -> List[Dict]:
        """
        Governance helper: Fetch LOOSE query bricks for a specific topic.
        """
        # Postgres JSONB query
        query = """
            SELECT id, type, data, created_at 
            FROM graph.nodes 
            WHERE type = 'brick' 
            AND data->>'lifecycle' = 'loose'
            AND data->'metadata'->>'sync_topic_id' = %s
        """
        rows = self._fetch_all(query, (topic_id,))
        
        results = []
        for r in rows:
            data = json.loads(r[2])
            results.append({
                "id": r[0],
                "type": r[1],
                "created_at": r[3],
                **data
            })
        return results

    def mark_forming(self, brick_id: str, resolved_by: str, actor: str):
        """
        Transition a brick to FORMING state with resolution metadata.

        B-01 FIX: graph.nodes is the SINGLE authority for lifecycle state.
        The sync.bricks fallback read path has been removed. If a brick does
        not exist in graph.nodes it has not been migrated yet and the caller
        MUST run sync_bricks_to_nodes() first. No alternate truth path is
        permitted here — doing so would allow the next migration sweep to
        silently reverse a FORMING promotion back to loose.
        """
        data = self._get_node_data(brick_id)
        if not data:
            # B-01: Do NOT fall back to sync.bricks. Raising here is correct.
            # The brick has not been projected into the unified node store yet.
            # Callers must ensure sync_bricks_to_nodes() has run before
            # attempting lifecycle mutations.
            raise ValueError(
                f"Brick {brick_id} not found in graph.nodes. "
                f"Run sync_bricks_to_nodes() before mutating lifecycle state. "
                f"Falling back to sync.bricks is forbidden — it creates dual authority."
            )

        # Monotonic check — idempotent if already advanced
        current = data.get("lifecycle", "loose")
        if current != "loose":
            return  # Already moved forward; idempotent success

        data["lifecycle"] = "forming"
        data.setdefault("metadata", {})
        data["metadata"]["resolved_by"] = resolved_by
        data["metadata"]["actor"] = actor
        data["metadata"]["resolved_at"] = datetime.now(timezone.utc).isoformat()

        if self._is_adapter():
            with self.db.transaction() as cur:
                self._mark_forming_logic(cur, brick_id, data, actor, resolved_by)
        else:  # Cursor already in transaction
            self._mark_forming_logic(self.db, brick_id, data, actor, resolved_by)

    def _mark_forming_logic(self, cur, brick_id, data, actor: str = "system", resolved_by: str = ""):
        # Single write path: graph.nodes is authoritative.
        # sync.bricks is updated as a projection mirror ONLY — not read for truth.
        cur.execute("UPDATE graph.nodes SET data=%s WHERE id=%s", (json.dumps(data), brick_id))
        # Mirror the state into sync.bricks for backward-compat read queries only.
        # This write is best-effort: its failure does NOT invalidate the lifecycle
        # mutation above, because graph.nodes is the sole authority.
        try:
            # FZ-01: Monotonicity guard on the mirror write.
            # Only advance sync.bricks state if it is currently BEHIND 'FORMING'.
            # States FINAL and SUPERSEDED are equal-or-ahead in the lifecycle —
            # writing 'FORMING' over them would collapse supersession lineage and
            # cause the next sync_bricks_to_nodes() sweep to project the wrong
            # lifecycle into graph.nodes.
            # States NOT IN ('SUPERSEDED', 'FINAL') = {IMPROVISE, FORMING} — safe to update.
            cur.execute(
                "UPDATE sync.bricks SET state = 'FORMING', lifecycle = 'Forming' WHERE id = %s "
                "AND state NOT IN ('SUPERSEDED', 'FINAL')",
                (brick_id,)
            )
        except Exception as mirror_err:
            # Log but do not re-raise: the authoritative write (graph.nodes) succeeded.
            print(f"[WARN] FZ-01: sync.bricks mirror update failed for {brick_id}: {mirror_err}. "
                  f"graph.nodes lifecycle is authoritative and correct.")

        self._log_audit_event(
            event_type="BRICK_RESOLVED",
            agent=actor,
            component="resolver",
            decision_action=DecisionAction.ACCEPTED,
            reason="Deterministic structural match with user input",
            metadata={"brick_id": brick_id, "resolved_by": resolved_by}
        )

    def get_intent_brick_counts(self, intent_id: str) -> Dict[str, int]:
        """
        Governance helper: Count bricks associated with an intent, grouped by lifecycle.
        Uses DERIVED_FROM edges (Intent -> Source) where source is a brick.
        """
        query = """
            SELECT n.data->>'lifecycle' as lifecycle, COUNT(*)
            FROM graph.nodes n
            JOIN graph.edges e ON n.id = e.target_id
            WHERE e.source_id = %s 
              AND e.edge_type = 'derived_from'
              AND n.type = 'brick'
            GROUP BY n.data->>'lifecycle'
        """
        rows = self._fetch_all(query, (intent_id,))
        
        counts = {
            "LOOSE": 0,
            "FORMING": 0,
            "FROZEN": 0,
            "CONFLICT": 0
        }
        
        for r in rows:
            lifecycle = (r[0] or "LOOSE").upper()
            if lifecycle in counts:
                counts[lifecycle] = int(r[1])
            else:
                # Map other states to reasonable categories if needed
                if lifecycle == "KILLED":
                    # KILLED bricks don't typically count towards intent formation
                    pass
                
        return counts

    def get_all_nodes_raw(self) -> List[Dict]:
        """
        Retrieve all nodes as dictionaries suitable for API response.
        """
        # 1. Get explicit graph nodes
        rows = self._fetch_all("SELECT id, type, data, created_at FROM graph.nodes")
        
        nodes = []
        for r in rows:
            data = json.loads(r[2])
            nodes.append({
                "id": r[0],
                "type": r[1],
                "created_at": r[3],
                **data
            })
            
        return nodes

    def sync_bricks_to_nodes(self, limit: int = 1000):
        """
        Migrate bricks from the 'bricks' sync table into the unified 'nodes' table.
        This enforces a single physical storage schema for all graph entities.
        """
        try:
            if self._is_adapter():
                with self.db.transaction() as cur:
                    self._sync_bricks_to_nodes_logic(cur, limit)
            else: # Cursor
                self._sync_bricks_to_nodes_logic(self.db, limit)
        except Exception as e:
            print(f"[SYNC] Migration skipped: {e}")

    def _sync_bricks_to_nodes_logic(self, cur, limit):
        # Optimization: Quick count check
        cur.execute("SELECT COUNT(*) FROM sync.bricks WHERE id NOT IN (SELECT id FROM graph.nodes)")
        pending = cur.fetchone()[0]
        if pending == 0:
            return

        # 1. Fetch bricks that aren't yet in the 'nodes' table
        cur.execute(f"""
            SELECT b.id, b.content, b.state, b.created_at, b.topic_id, t.display_name
            FROM sync.bricks b
            LEFT JOIN sync.topics t ON b.topic_id = t.id
            WHERE b.id NOT IN (SELECT id FROM graph.nodes)
            LIMIT {limit}
        """)
        brick_rows = cur.fetchall()
        
        # 2. Insert them as nodes
        state_map = {
            "IMPROVISE": "loose",
            "FORMING": "forming",
            "FINAL": "frozen",
            "SUPERSEDED": "killed"
        }
        
        for br in brick_rows:
            brick_id = br[0]
            content = br[1]
            state = br[2]
            created_at = br[3]
            topic_id = br[4]
            topic_name = br[5]
            
            node_data = {
                "statement": content,
                "lifecycle": state_map.get(state, "loose"),
                "metadata": {
                    "sync_topic_id": topic_id,
                    "sync_topic_name": topic_name
                }
            }
            
            cur.execute(
                "INSERT INTO graph.nodes (id, type, data, created_at) VALUES (%s, 'brick', %s, %s)",
                (brick_id, json.dumps(node_data), created_at)
            )
            
            # 3. If topic node doesn't exist, create it
            if topic_id:
                cur.execute("SELECT id FROM graph.nodes WHERE id = %s", (f"topic_{topic_id}",))
                if not cur.fetchone():
                    cur.execute(
                        "INSERT INTO graph.nodes (id, type, data, created_at) VALUES (%s, 'topic', %s, %s)",
                        (f"topic_{topic_id}", json.dumps({"name": topic_name or topic_id}), created_at)
                    )
                
                # 4. Create edge between topic and brick
                cur.execute(
                    "INSERT INTO graph.edges (source_id, target_id, edge_type, created_at) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                    (f"topic_{topic_id}", brick_id, EdgeType.ASSEMBLED_IN.value, created_at)
                )

        print(f"[SYNC] Migrated {len(brick_rows)} bricks to unified node storage.")

    def get_all_edges_raw(self) -> List[Dict]:
        """
        Retrieve all edges as dictionaries suitable for API response.
        """
        rows = self._fetch_all("SELECT source_id, target_id, edge_type, metadata FROM graph.edges")
        
        edges = []
        for r in rows:
            data = r[3] if isinstance(r[3], dict) else json.loads(r[3] if r[3] else "{}")
            edges.append({
                "source": r[0],
                "target": r[1],
                "type": r[2],
                **data
            })
        return edges

    def query_audit_logs(self, filters: Dict[str, Any] = None) -> List[Dict]:
        """
        Governance Analytics: Query the governance.audit_trace table.
        """
        query = "SELECT payload FROM governance.audit_trace"
        params = []
        
        if filters:
            conditions = []
            for k, v in filters.items():
                conditions.append(f"payload->>'{k}' = %s")
                params.append(str(v))
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY created_at DESC LIMIT 1000"
        
        rows = self._fetch_all(query, tuple(params))
        return [row[0] if isinstance(row[0], dict) else json.loads(row[0]) for row in rows]
