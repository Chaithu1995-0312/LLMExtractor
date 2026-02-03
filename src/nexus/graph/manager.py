import json
import os
from typing import Dict, Any, Tuple

class GraphManager:
    def __init__(self):
        self.graph_dir = os.path.dirname(os.path.abspath(__file__))
        self.nodes_path = os.path.join(self.graph_dir, "nodes.json")
        self.edges_path = os.path.join(self.graph_dir, "edges.json")

    def _load_json(self, path: str) -> list:
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_json(self, path: str, data: list):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def register_node(self, node_type: str, node_id: str, attrs: Dict[str, Any]):
        """
        Register a node in the graph. Idempotent.
        """
        nodes = self._load_json(self.nodes_path)
        
        # Check for existence
        for node in nodes:
            if node.get("id") == node_id:
                # Already exists. In a more complex system, we might merge attrs.
                # For now, we assume immutability/idempotency.
                return

        new_node = {
            "id": node_id,
            "type": node_type,
            **attrs
        }
        nodes.append(new_node)
        self._save_json(self.nodes_path, nodes)

    def register_edge(self, src: Tuple[str, str], dst: Tuple[str, str], edge_type: str):
        """
        Register an edge. Idempotent.
        src = (type, id)
        dst = (type, id)
        """
        edges = self._load_json(self.edges_path)
        
        # We store source/target as IDs in the JSON, but maybe we should store type too?
        # The existing edges.json uses "source": "id", "target": "id".
        # We will follow that convention, assuming IDs are globally unique or we don't care about type in the edge definition itself (it's implicit in the node).
        # However, "src" parameter is a tuple. I'll use src[1] (the ID).
        
        src_id = src[1]
        dst_id = dst[1]
        
        for edge in edges:
            if (edge.get("source") == src_id and 
                edge.get("target") == dst_id and 
                edge.get("type") == edge_type):
                return

        new_edge = {
            "source": src_id,
            "target": dst_id,
            "type": edge_type
        }
        edges.append(new_edge)
        self._save_json(self.edges_path, edges)
