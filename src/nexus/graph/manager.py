import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, List, Optional
from nexus.graph.schema import Intent, Source, ScopeNode, Edge, EdgeType, IntentLifecycle, IntentType, GraphNode

class GraphManager:
    def __init__(self, db_path: str = None):
        self.graph_dir = os.path.dirname(os.path.abspath(__file__))
        if db_path is None:
            db_path = os.path.join(self.graph_dir, "graph.db")
        self.db_path = db_path
        self._init_db()

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
        c = conn.cursor()
        try:
            # Check if exists
            c.execute("SELECT data FROM nodes WHERE id = ?", (node_id,))
            row = c.fetchone()
            
            if row:
                if merge:
                    existing_data = json.loads(row[0])
                    existing_data.update(attrs)
                    c.execute(
                        "UPDATE nodes SET data = ? WHERE id = ?",
                        (json.dumps(existing_data), node_id)
                    )
                    conn.commit()
                return # Already exists or updated
            
            # Insert
            c.execute(
                "INSERT INTO nodes (id, type, data, created_at) VALUES (?, ?, ?, datetime('now'))",
                (node_id, node_type, json.dumps(attrs))
            )
            conn.commit()
        except Exception as e:
            print(f"Error registering node {node_id}: {e}")
        finally:
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
        c.execute(query, (topic_node_id, EdgeType.ASSEMBLED_IN.value)) # Note: Check Edge direction in assembler
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
        
        conn = self._get_conn()
        c = conn.cursor()
        try:
            c.execute(
                "SELECT type FROM edges WHERE source=? AND target=? AND type=?",
                (src_id, dst_id, edge_type_str)
            )
            if c.fetchone():
                return

            c.execute(
                "INSERT INTO edges (source, target, type, data, created_at) VALUES (?, ?, ?, ?, datetime('now'))",
                (src_id, dst_id, edge_type_str, json.dumps(attrs or {}))
            )
            conn.commit()
        except Exception as e:
            print(f"Error registering edge {src_id}->{dst_id}: {e}")
        finally:
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

    def _log_audit_event(self, event_type: str, payload: Dict[str, Any]):
        """
        Log an audit event. For now, we print to console.
        In Phase 3, this will append to phase3_audit_trace.jsonl.
        """
        # ISO8601 timestamp
        ts = datetime.now(timezone.utc).isoformat()
        event = {
            "timestamp": ts,
            "event": event_type,
            **payload
        }
        print(f"[AUDIT] {json.dumps(event)}")
        # TODO: Append to services/cortex/phase3_audit_trace.jsonl if needed by strict requirements

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
        c = conn.cursor()
        c.execute("UPDATE nodes SET data=? WHERE id=?", (json.dumps(data), node_id))
        conn.commit()
        conn.close()

        # Audit
        self._log_audit_event("NODE_KILLED", {
            "node_id": node_id,
            "reason": reason,
            "actor": actor,
            "previous_state": current_state.value
        })

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
        c = conn.cursor()
        c.execute("UPDATE nodes SET data=? WHERE id=?", (json.dumps(data), node_id))
        conn.commit()
        conn.close()

        self._log_audit_event("NODE_FROZEN", {
            "node_id": node_id,
            "promoted_bricks": promote_bricks,
            "actor": actor
        })

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

        # 1. Create Edge
        edge = Edge(
            source_id=old_node_id,
            target_id=new_node_id,
            edge_type=EdgeType.SUPERSEDED_BY,
            metadata={
                "reason": reason,
                "actor": actor,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        self.add_typed_edge(edge)

        # 2. Update Node Metadata (Old)
        old_data["superseded_by"] = new_node_id
        
        # 3. Update Node Metadata (New)
        new_data["supersedes"] = list(set(new_data.get("supersedes", []) + [old_node_id]))

        # Persist Nodes
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("UPDATE nodes SET data=? WHERE id=?", (json.dumps(old_data), old_node_id))
        c.execute("UPDATE nodes SET data=? WHERE id=?", (json.dumps(new_data), new_node_id))
        conn.commit()
        conn.close()

        self._log_audit_event("NODE_SUPERSEDED", {
            "old_node": old_node_id,
            "new_node": new_node_id,
            "reason": reason,
            "actor": actor
        })

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
        c = conn.cursor()
        c.execute("UPDATE nodes SET data=? WHERE id=?", (json.dumps(data), intent_id))
        conn.commit()
        conn.close()

    def add_typed_edge(self, edge: Edge):
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
                    raise ValueError(f"Target {edge.target_id} already overridden by {existing[0][0]}")

        self.register_edge(
            ("node", edge.source_id), # Generic type as we rely on ID
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
        c = conn.cursor()
        try:
            # Delete edges where this node is source or target
            c.execute("DELETE FROM edges WHERE source = ? OR target = ?", (node_id, node_id))
            
            # Delete the node
            c.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
            
            conn.commit()
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
        c.execute("SELECT id, type, data, created_at FROM nodes")
        rows = c.fetchall()
        conn.close()
        
        nodes = []
        for r in rows:
            data = json.loads(r[2])
            # Merge fields
            node = {
                "id": r[0],
                "type": r[1],
                "created_at": r[3],
                **data
            }
            nodes.append(node)
        return nodes

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
