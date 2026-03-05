import json
from typing import List, Dict, Any
from nexus.evolution.reflection_engine import ReflectionEngine
from nexus.graph.manager import GraphManager

class StrategicAdvisor:
    """
    Strategic Advisor Layer (L6).
    Translates reflection patterns into actionable advice.
    """
    def __init__(self):
        self.reflection = ReflectionEngine()
        self.graph = GraphManager()

    def generate_advice(self) -> List[Dict[str, Any]]:
        """
        Analyzes the reflection report and produces strategic suggestions.
        """
        report = self.reflection.analyze_thinking_patterns()
        advice = []
        
        # 1. High Momentum Advice
        if report["intent_momentum"]:
            top_project = report["intent_momentum"][0]
            advice.append({
                "type": "MOMENTUM_BOOST",
                "project_id": top_project["id"],
                "message": f"Project '{top_project['name']}' has high momentum ({top_project['weekly_count']} bricks this week). Consider allocating more focus here.",
                "severity": "info"
            })
            
        # 2. Stagnation Advice
        for stagnant in report["stagnant_projects"]:
            advice.append({
                "type": "STAGNATION_ALERT",
                "project_id": stagnant["id"],
                "message": f"Project '{stagnant['name']}' has been stagnant for over 30 days. Should we archive it or resume?",
                "severity": "warn"
            })
            
        # 3. Emit Advice to Pulse
        for item in advice:
            self.graph._emit_pulse(
                event_type="STRATEGIC_ADVICE",
                payload=item,
                topic_id=item.get("project_id"),
                severity=item["severity"],
                source="StrategicAdvisor"
            )
            
        return advice

if __name__ == "__main__":
    advisor = StrategicAdvisor()
    advice = advisor.generate_advice()
    print(json.dumps(advice, indent=2))
