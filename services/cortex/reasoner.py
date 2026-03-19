import json
import os


class GraphReasoner:
    def __init__(self, graph):
        self.graph = graph

    def load_history(self):
        path = "output/nexus_reports/processing_report.json"
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        return {}

    def find_patterns(self, node_type: str):
        if not hasattr(self.graph, "get_nodes_by_type") or not hasattr(self.graph, "get_neighbors"):
            return []

        nodes = self.graph.get_nodes_by_type(node_type)
        patterns = []

        history = self.load_history()
        history_loaded = bool(history)

        for node in nodes:
            neighbors = self.graph.get_neighbors(node["id"])
            if len(neighbors) > 3:
                patterns.append({
                    "node": node,
                    "pattern": "highly_connected",
                    "history_loaded": history_loaded,
                })

        return patterns

    def score_signal(self, node):
        if not hasattr(self.graph, "get_neighbors") or not isinstance(node, dict) or "id" not in node:
            return 0.0

        neighbors = self.graph.get_neighbors(node["id"])
        score = len(neighbors) * 0.2
        if node.get("confidence"):
            score += node["confidence"]
        return min(score, 1.0)
