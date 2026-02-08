import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, List, Optional, Union, Generator
from contextlib import contextmanager
from nexus.graph.schema import (
    Intent, Source, ScopeNode, Edge, EdgeType, IntentLifecycle, 
    IntentType, GraphNode, AuditEventType, ModelTier, DecisionAction
)
from nexus.config import GRAPH_DB_PATH, SYNC_SCHEMA_PATH, AUDIT_LOG_PATH

class GraphTransaction:
    """
    Context manager for SQLite transactions with nested (SAVEPOINT) support.
    """
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.savepoint_name = f"sp_{id(self)}"
        self.entered = False

    def __enter__(self):
        if not self.conn.in_transaction:
            self.conn.execute("BEGIN TRANSACTION")
            self.nested = False
        else:
            self.conn.execute(f"SAVEPOINT {self.savepoint_name}")
            self.nested = True
        self.entered = True
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.entered:
            return
        
        if exc_type is not None:
            if self.nested:
                self.conn.execute(f"ROLLBACK TO {self.savepoint_name}")
            else:
                self.conn.rollback()
        else:
            if self.nested:
                self.conn.execute(f"RELEASE SAVEPOINT {self.savepoint_name}")
            else:
                self.conn.commit()
        self.entered = False

class GraphManager:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or GRAPH_DB_PATH
        self._init_db()
        # Enforce unified storage on startup - Idempotent
        self.sync_bricks_to_nodes()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Nodes Table
        c.execute('''
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                data JSON NOT NULL,
                created_at TEXT
            )
        ''')
        
        # Edges Table
        c.execute('''
            CREATE TABLE IF NOT EXISTS edges (
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                type TEXT NOT NULL,
                data JSON,
                created_at TEXT,
                PRIMARY KEY (source, target, type),
                FOREIGN KEY(source) REFERENCES nodes(id),
                FOREIGN KEY(target) REFERENCES nodes(id)
            )
        ''')
        
        # Ensure Sync Schema exists
        if os.path.exists(SYNC_SCHEMA_PATH):
            with open(SYNC_SCHEMA_PATH, "r", encoding="utf-8") as f:
                schema_sql = f.read()
            c.executescript(schema_sql)

        conn.commit()
        conn.close()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def register_node(self, node_type: str, node_id: str, attrs: Dict[str, Any], merge: bool = False):
        """
        Register a generic node. Idempotent by default.
        If merge=True, updates existing node data.
        """
        conn = self._get_conn()
        with GraphTransaction(conn) as c:
            try:
                # Check if exists
                res = c.execute("SELECT data FROM nodes WHERE id = ?", (node_id,))
                row = res.fetchone()
                
                if row:
                    if merge:
                        existing_data = json.loads(row[0])
                        existing_data.update(attrs)
                        c.execute(
                            "UPDATE nodes SET data = ? WHERE id = ?",
                            (json.dumps(existing_data), node_id)
                        )
                    return # Already exists or updated
                
                # Insert
                c.execute(
                    "INSERT INTO nodes (id, type, data, created_at) VALUES (?, ?, ?, datetime('now'))",
                    (node_id, node_type, json.dumps(attrs))
                )
            except Exception as e:
                print(f"Error registering node {node_id}: {e}")
                raise
        conn.close()

    def get_intents_by_topic(self, topic_node_id: str) -> List[Intent]:
        """
        Retrieve all intents linked to a specific topic.
        """
        conn = self._get_conn()
        c = conn.cursor()
        query = """
            SELECT n.id, n.data, n.created_at 
            FROM nodes n
            JOIN edges e ON n.id = e.target
            WHERE e.source = ? AND e.type = ? AND n.type = 'intent'
        """
        c.execute(query, (topic_node_id, EdgeType.ASSEMBLED_IN.value))
        rows = c.fetchall()
        conn.close()
        
        intents = []
        for r in rows:
            data = json.loads(r[1])
            i = Intent(
                id=r[0],
                created_at=r[2],
                statement=data.get("statement", ""),
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
            conn = self._get_conn()
            c = conn.cursor()
            c.execute("SELECT target FROM edges WHERE source=? AND type=?", (current_id, edge_type_str))
            targets = [row[0] for row in c.fetchall()]
            conn.close()
            
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

        conn = self._get_conn()
        with GraphTransaction(conn) as c:
            try:
                res = c.execute(
                    "SELECT type FROM edges WHERE source=? AND target=? AND type=?",
                    (src_id, dst_id, edge_type_str)
                )
                if res.fetchone():
                    return

                c.execute(
                    "INSERT INTO edges (source, target, type, data, created_at) VALUES (?, ?, ?, ?, datetime('now'))",
                    (src_id, dst_id, edge_type_str, json.dumps(attrs or {}))
                )
            except Exception as e:
                print(f"Error registering edge {src_id}->{dst_id}: {e}")
                raise
        conn.close()

    # Typed helpers for new Schema
    def add_intent(self, intent: Intent):
        data = {
            "statement": intent.statement,
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
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT data FROM nodes WHERE id=?", (node_id,))
        row = c.fetchone()
        conn.close()
        if row:
            return json.loads(row[0])
        return None

    def get_node(self, node_id: str) -> Optional[Tuple[str, Dict]]:
        """
        Retrieve node type and data.
        Returns (type, data_dict) or None.
        """
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT type, data FROM nodes WHERE id=?", (node_id,))
        row = c.fetchone()
        conn.close()
        if row:
            return (row[0], json.loads(row[1]))
        return None

    def _emit_pulse(self, event_type: str, data: Dict):
        """
        Fire-and-forget call to the L1 Narrator.
        In a real app, use a background task queue (Celery/RQ).
        For this script, we can do a quick POST or print.
        """
        try:
            # We assume the gateway is running or we import it for a quick local call
            # For simplicity, we just print the 'Intent' of the pulse here.
            # In full implementation, this calls JarvisGateway.pulse()
            print(f"⚡ [PULSE L1] {event_type}: {data}")
        except:
            pass

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
        Log a standardized audit event. Appends to phase3_audit_trace.jsonl.
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
        
        # Append to AUDIT_LOG_PATH
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)
            
            with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            print(f"ERROR: Failed to write to audit log: {e}")

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
        conn = self._get_conn()
        with GraphTransaction(conn) as c:
            c.execute("UPDATE nodes SET data=? WHERE id=?", (json.dumps(data), node_id))
        conn.close()

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
        conn = self._get_conn()
        with GraphTransaction(conn) as c:
            c.execute("UPDATE nodes SET data=? WHERE id=?", (json.dumps(data), node_id))
        conn.close()

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

        conn = self._get_conn()
        with GraphTransaction(conn) as c:
            # 1. Create Edge
            self.register_edge(
                ("node", old_node_id),
                ("node", new_node_id),
                EdgeType.SUPERSEDED_BY.value,
                {
                    "reason": reason,
                    "actor": actor,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )

            # 2. Update Node Metadata (Old)
            old_data["superseded_by"] = new_node_id
            
            # 3. Update Node Metadata (New)
            new_data["supersedes"] = list(set(new_data.get("supersedes", []) + [old_node_id]))

            # Persist Nodes
            c.execute("UPDATE nodes SET data=? WHERE id=?", (json.dumps(old_data), old_node_id))
            c.execute("UPDATE nodes SET data=? WHERE id=?", (json.dumps(new_data), new_node_id))
            
        conn.close()

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
        conn = self._get_conn()
        with GraphTransaction(conn) as c:
            c.execute("UPDATE nodes SET data=? WHERE id=?", (json.dumps(data), intent_id))
        conn.close()

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
            conn = self._get_conn()
            c = conn.cursor()
            c.execute("SELECT source FROM edges WHERE target=? AND type=?", (edge.target_id, EdgeType.OVERRIDES.value))
            existing = c.fetchall()
            conn.close()
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
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT id, data, created_at FROM nodes WHERE type='intent'")
        rows = c.fetchall()
        conn.close()
        
        intents = []
        for r in rows:
            data = json.loads(r[1])
            i = Intent(
                id=r[0],
                created_at=r[2],
                statement=data.get("statement", ""),
                lifecycle=IntentLifecycle(data.get("lifecycle", "loose")),
                intent_type=IntentType(data.get("intent_type", "unknown")),
                metadata=data.get("metadata", {})
            )
            intents.append(i)
        return intents

    def get_all_edges(self) -> List[Edge]:
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT source, target, type, data FROM edges")
        rows = c.fetchall()
        conn.close()
        
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
        conn = self._get_conn()
        c = conn.cursor()
        # Outgoing
        c.execute("SELECT source, target, type, data FROM edges WHERE source=?", (node_id,))
        out_rows = c.fetchall()
        # Incoming
        c.execute("SELECT source, target, type, data FROM edges WHERE target=?", (node_id,))
        in_rows = c.fetchall()
        conn.close()
        
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
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT id, data, created_at FROM nodes WHERE type='scope'")
        rows = c.fetchall()
        conn.close()
        
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
    
    def get_all_sources(self) -> Dict[str, Source]:
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT id, data, created_at FROM nodes WHERE type='source'")
        rows = c.fetchall()
        conn.close()

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
        conn = self._get_conn()
        try:
            with GraphTransaction(conn) as c:
                # Delete edges where this node is source or target
                c.execute("DELETE FROM edges WHERE source = ? OR target = ?", (node_id, node_id))
                
                # Delete the node
                c.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
            return True
        except Exception as e:
            print(f"Error deleting node {node_id}: {e}")
            return False
        finally:
            conn.close()

    def get_all_nodes_raw(self) -> List[Dict]:
        """
        Retrieve all nodes as dictionaries suitable for API response.
        """
        conn = self._get_conn()
        c = conn.cursor()
        
        # 1. Get explicit graph nodes
        c.execute("SELECT id, type, data, created_at FROM nodes")
        rows = c.fetchall()
        
        nodes = []
        for r in rows:
            data = json.loads(r[2])
            nodes.append({
                "id": r[0],
                "type": r[1],
                "created_at": r[3],
                **data
            })
            
        conn.close()
        return nodes

    def sync_bricks_to_nodes(self, limit: int = 1000):
        """
        Migrate bricks from the 'bricks' sync table into the unified 'nodes' table.
        This enforces a single physical storage schema for all graph entities.
        """
        conn = self._get_conn()
        
        try:
            with GraphTransaction(conn) as c:
                # Optimization: Quick count check
                res = c.execute("SELECT COUNT(*) FROM bricks WHERE id NOT IN (SELECT id FROM nodes)")
                pending = res.fetchone()[0]
                if pending == 0:
                    return

                # 1. Fetch bricks that aren't yet in the 'nodes' table
                res = c.execute(f"""
                    SELECT b.id, b.content, b.state, b.created_at, b.topic_id, t.display_name
                    FROM bricks b
                    LEFT JOIN topics t ON b.topic_id = t.id
                    WHERE b.id NOT IN (SELECT id FROM nodes)
                    LIMIT {limit}
                """)
                brick_rows = res.fetchall()
                
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
                    
                    c.execute(
                        "INSERT INTO nodes (id, type, data, created_at) VALUES (?, 'brick', ?, ?)",
                        (brick_id, json.dumps(node_data), created_at)
                    )
                    
                    # 3. If topic node doesn't exist, create it
                    if topic_id:
                        res_topic = c.execute("SELECT id FROM nodes WHERE id = ?", (f"topic_{topic_id}",))
                        if not res_topic.fetchone():
                            c.execute(
                                "INSERT INTO nodes (id, type, data, created_at) VALUES (?, 'topic', ?, ?)",
                                (f"topic_{topic_id}", json.dumps({"name": topic_name or topic_id}), created_at)
                            )
                        
                        # 4. Create edge between topic and brick
                        c.execute(
                            "INSERT OR IGNORE INTO edges (source, target, type, created_at) VALUES (?, ?, ?, ?)",
                            (f"topic_{topic_id}", brick_id, EdgeType.ASSEMBLED_IN.value, created_at)
                        )

            print(f"[SYNC] Migrated {len(brick_rows)} bricks to unified node storage.")
        except sqlite3.OperationalError as e:
            print(f"[SYNC] Migration skipped: {e}")
        finally:
            conn.close()

    def get_all_edges_raw(self) -> List[Dict]:
        """
        Retrieve all edges as dictionaries suitable for API response.
        """
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT source, target, type, data FROM edges")
        rows = c.fetchall()
        conn.close()
        
        edges = []
        for r in rows:
            data = json.loads(r[3] if r[3] else "{}")
            edges.append({
                "source": r[0],
                "target": r[1],
                "type": r[2],
                **data
            })
        return edges

    def query_audit_logs(self, filters: Dict[str, Any] = None) -> List[Dict]:
        """
        Governance Analytics: Query the audit JSONL file.
        In-memory table approach for fast analysis.
        """
        if not os.path.exists(AUDIT_LOG_PATH):
            return []

        events = []
        with open(AUDIT_LOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    ev = json.loads(line)
                    # Apply simple filters
                    match = True
                    if filters:
                        for k, v in filters.items():
                            if ev.get(k) != v:
                                match = False
                                break
                    if match:
                        events.append(ev)
                except json.JSONDecodeError:
                    continue
        
        return events
