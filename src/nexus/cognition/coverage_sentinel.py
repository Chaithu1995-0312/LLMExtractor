import json
import uuid
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from collections import deque

from nexus.sync.llm import LLMClient
from nexus.graph.schema import AuditEventType, DecisionAction
from nexus.config import get_agent_config
from nexus.cognition.goal_engine import GoalEngine

class CoverageSentinel:
    def __init__(self, llm_client: LLMClient, history_size: int = 100):
        self.llm_client = llm_client
        self.config = get_agent_config("coverage_sentinel")
        self.goal_engine = GoalEngine() # Uses default db adapter
        
        # Override history size if config specifies it and default was passed
        if history_size == 100 and "history_size" in self.config:
             history_size = self.config["history_size"]
             
        self.recent_fingerprints = deque(maxlen=history_size)

    def analyze_topic(self, topic_id: str, bricks: List[Dict[str, Any]], intents: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        Analyzes a topic's content (bricks and intents) for structural weaknesses.
        Emits Coverage Alerts.
        """
        if not bricks:
            return []

        # Prepare Prompt Data
        brick_text = "\n".join([f"{b['id']}: {b.get('content', '')}" for b in bricks])
        
        intent_text = ""
        if intents:
            intent_text = "\n".join([f"{i['id']}: {i.get('statement', '')}" for i in intents])

        system_prompt = self.config.get("system_prompt", """You are CoverageSentinel.

Your role is to detect structural weaknesses in a knowledge topic.
You do NOT create facts.
You do NOT rewrite content.
You do NOT answer user questions.

You only observe and report.

Input:
- A topic name
- A list of bricks (short factual statements)
- Optional intent groupings

Your task:
1. Detect semantic redundancy (same idea repeated).
2. Detect missing implied questions.
3. Detect high-signal bricks not used in any intent.
4. Detect contradictions if present.
5. Detect "Analysis without Declaration": If you observe extensive analysis, explanation, or synthesis without any explicit user or system declaration of rules, invariants, constraints, or guarantees, emit an ANALYSIS_WITHOUT_DECLARATION alert.

Rules:
- Be conservative but firm on declarations. If analysis exists without explicit rules, flag it.
- Never hallucinate missing content.
- Use short, precise language.
- Output MUST be valid JSON only.
- Follow the provided schema exactly.
- Signal score reflects confidence, not importance.

Schema for Alert Object:
{
  "alert_id": "string (uuid)",
  "type": "FLOW_REDUNDANCY | COVERAGE_GAP | ORPHAN_BRICKS | CONTRADICTION | LOW_SIGNAL_TOPIC | ANALYSIS_WITHOUT_DECLARATION",
  "topic_id": "string",
  "severity": "info | warning | critical",
  "signal_score": number (0.0 to 1.0),
  "generated_at": "string (iso8601)",
  "source": "CoverageSentinel",
  "details": {
    "summary": "string",
    "affected_brick_ids": ["string"],
    "missing_questions": ["string"],
    "suggested_actions": ["string"]
  }
}

Output a JSON object with a key "alerts" containing a list of these objects.
""")

        user_prompt = f"""
Topic: {topic_id}

Bricks:
{brick_text}

Intents (optional):
{intent_text}
"""

        # Call LLM (L1 Local)
        try:
            intent_class = self.config.get("intent_class", "COVERAGE_ANALYSIS")
            cost_tolerance = self.config.get("cost_tolerance", "zero")

            response = self.llm_client.generate(
                system_prompt=system_prompt, 
                user_prompt=user_prompt, 
                intent_class=intent_class, 
                cost_tolerance=cost_tolerance,
                user_visible=False
            )
            
            cleaned_response = self._clean_llm_response(response)
            data = json.loads(cleaned_response)
            alerts = data.get("alerts", [])
            
            # Post-processing: Ensure IDs and Timestamps are present if LLM missed them
            processed_alerts = []
            for alert in alerts:
                if "alert_id" not in alert:
                    alert["alert_id"] = str(uuid.uuid4())
                if "generated_at" not in alert:
                    alert["generated_at"] = datetime.now(timezone.utc).isoformat()
                if "source" not in alert:
                    alert["source"] = "CoverageSentinel"
                if "topic_id" not in alert:
                    alert["topic_id"] = topic_id
                
                # Fingerprinting & Deduplication
                fingerprint = self._generate_fingerprint(alert)
                alert["fingerprint"] = fingerprint # For Audit Correlation
                
                if fingerprint in self.recent_fingerprints:
                    alert["is_duplicate"] = True
                else:
                    alert["is_duplicate"] = False
                    self.recent_fingerprints.append(fingerprint)

                    # SELF-REPAIR: If a critical gap is found, create a goal
                    self._trigger_repair_goal(alert)
                
                processed_alerts.append(alert)
            
            return processed_alerts

        except Exception as e:
            print(f"[CoverageSentinel] Analysis failed: {e}")
            return []

    def _trigger_repair_goal(self, alert: Dict[str, Any]):
        """
        Creates a goal in the Goal Engine if the alert warrants intervention.
        """
        alert_type = alert.get("type")
        severity = alert.get("severity")
        
        # Only act on non-duplicate, actionable alerts
        if alert.get("is_duplicate"):
            return

        target_types = ["COVERAGE_GAP", "LOW_SIGNAL_TOPIC", "ANALYSIS_WITHOUT_DECLARATION"]
        
        if alert_type in target_types:
            topic_id = alert.get("topic_id")
            details = alert.get("details", {})
            summary = details.get("summary", "Unknown Issue")
            
            description = f"Resolve {alert_type} in topic {topic_id}: {summary}"
            
            print(f"[CoverageSentinel] Auto-creating goal for {alert_type}")
            
            self.goal_engine.create_goal(
                description=description,
                priority=10 if severity == 'critical' else 5,
                metadata={
                    "source": "CoverageSentinel",
                    "alert_id": alert.get("alert_id"),
                    "topic_id": topic_id,
                    "alert_details": details
                }
            )

    def _generate_fingerprint(self, alert: Dict[str, Any]) -> str:
        """
        Generates a deterministic fingerprint for an alert.
        fingerprint = hash(type + topic_id + sorted(affected_brick_ids))
        """
        alert_type = alert.get("type", "UNKNOWN")
        topic_id = alert.get("topic_id", "UNKNOWN")
        details = alert.get("details", {})
        
        # Sort brick IDs for stability
        affected_bricks = sorted(details.get("affected_brick_ids", []))
        # If no bricks, use summary or missing questions to ensure uniqueness of different issues
        extra_context = ""
        if not affected_bricks:
            extra_context = details.get("summary", "") + str(sorted(details.get("missing_questions", [])))
            
        raw_string = f"{alert_type}:{topic_id}:{','.join(affected_bricks)}:{extra_context}"
        return hashlib.sha256(raw_string.encode()).hexdigest()

    def _clean_llm_response(self, response: str) -> str:
        """Helper to extract JSON from LLM markdown."""
        if "```json" in response:
            return response.split("```json")[1].split("```")[0].strip()
        if "```" in response:
            return response.split("```")[1].split("```")[0].strip()
        return response.strip()
