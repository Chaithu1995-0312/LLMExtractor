import json
import uuid
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from collections import deque

from nexus.sync.llm import LLMClient
from nexus.graph.schema import AuditEventType, DecisionAction

class CoverageSentinel:
    def __init__(self, llm_client: LLMClient, history_size: int = 100):
        self.llm_client = llm_client
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

        system_prompt = """You are CoverageSentinel.

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

Rules:
- Be conservative. If unsure, do not emit an alert.
- Never hallucinate missing content.
- Use short, precise language.
- Output MUST be valid JSON only.
- Follow the provided schema exactly.
- Signal score reflects confidence, not importance.

Schema for Alert Object:
{
  "alert_id": "string (uuid)",
  "type": "FLOW_REDUNDANCY | COVERAGE_GAP | ORPHAN_BRICKS | CONTRADICTION | LOW_SIGNAL_TOPIC",
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
"""

        user_prompt = f"""
Topic: {topic_id}

Bricks:
{brick_text}

Intents (optional):
{intent_text}
"""

        # Call LLM (L1 Local)
        try:
            response = self.llm_client.generate(
                system_prompt=system_prompt, 
                user_prompt=user_prompt, 
                intent_class="COVERAGE_ANALYSIS", 
                cost_tolerance="zero",
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
                
                processed_alerts.append(alert)
            
            return processed_alerts

        except Exception as e:
            print(f"[CoverageSentinel] Analysis failed: {e}")
            return []

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
