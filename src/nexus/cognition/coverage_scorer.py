from typing import Dict, Any, List
from nexus.graph.manager import GraphManager
from nexus.governance.alert_manager import AlertManager
from nexus.graph.schema import IntentLifecycle

class CoverageScorer:
    def __init__(self, graph_manager: GraphManager, alert_manager: AlertManager):
        self.graph_manager = graph_manager
        self.alert_manager = alert_manager

    def compute_score(self, topic_id: str) -> Dict[str, Any]:
        """
        Computes the coverage score for a topic.
        Formula: clamp(1.0 - 0.4*Gap - 0.2*Redundancy - 0.2*Orphan + 0.2*Stability, 0, 1)
        """
        alerts = self.alert_manager.get_alerts_for_topic(topic_id)
        active_alerts = [a for a in alerts if a['state'] in ['NEW', 'ACKNOWLEDGED']]
        
        gap_count = len([a for a in active_alerts if a['type'] == 'COVERAGE_GAP'])
        redundancy_count = len([a for a in active_alerts if a['type'] == 'FLOW_REDUNDANCY'])
        orphan_count = len([a for a in active_alerts if a['type'] == 'ORPHAN_BRICKS'])
        
        # Stability: Ratio of Frozen Intents
        intents = self.graph_manager.get_intents_by_topic(f"topic_{topic_id}")
        total_intents = len(intents)
        frozen_intents = len([i for i in intents if i.lifecycle == IntentLifecycle.FROZEN])
        
        stability_bonus = 0.0
        if total_intents > 0:
            stability_bonus = frozen_intents / total_intents

        # Penalties (Simplified normalization: 1 alert = full penalty? No, maybe capped)
        # Let's assume presence of *any* alert of a type triggers the penalty for now, or scale it.
        # "Gap Score 0-1" -> likely normalized. 
        # Let's say: Gap Score = min(gap_count * 0.2, 1.0)
        
        gap_score = min(gap_count * 0.2, 1.0)
        redundancy_penalty = min(redundancy_count * 0.2, 1.0)
        orphan_penalty = min(orphan_count * 0.2, 1.0)
        
        raw_score = 1.0 - (0.4 * gap_score) - (0.2 * redundancy_penalty) - (0.2 * orphan_penalty) + (0.2 * stability_bonus)
        coverage_score = max(0.0, min(1.0, raw_score))
        
        return {
            "topic_id": topic_id,
            "coverage_score": round(coverage_score, 2),
            "components": {
                "gap_score": gap_score,
                "redundancy_penalty": redundancy_penalty,
                "orphan_penalty": orphan_penalty,
                "stability_bonus": stability_bonus
            }
        }
