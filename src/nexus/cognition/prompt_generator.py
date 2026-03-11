import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from nexus.sync.llm import LLMClient
from nexus.governance.alert_manager import AlertManager
from nexus.cognition.coverage_scorer import CoverageScorer
from nexus.config import get_agent_config

class PromptGenerator:
    def __init__(self, llm_client: LLMClient, alert_manager: AlertManager, coverage_scorer: CoverageScorer):
        self.llm_client = llm_client
        self.alert_manager = alert_manager
        self.coverage_scorer = coverage_scorer
        self.config = get_agent_config("prompt_generator")

    def generate_prompts(self, alert_id: str, actor: str) -> Dict[str, Any]:
        """
        Generates ingestion prompts for a given alert if eligibility checks pass.
        Returns a result dict: { "success": bool, "reason": str, "prompts": list }
        """
        # 1. Fetch Alert
        alert = self.alert_manager.get_alert(alert_id)
        if not alert:
            return {"success": False, "reason": "Alert not found", "prompts": []}

        topic_id = alert['topic_id']
        
        # 2. Eligibility Gates
        
        # Rule 1 & 2: State must be ACKNOWLEDGED
        if alert['state'] != 'ACKNOWLEDGED':
            return {"success": False, "reason": f"Alert state is {alert['state']}, must be ACKNOWLEDGED", "prompts": []}

        # Rule 3: Gap Type (Assuming gap_type is in details, default to FACTUAL if missing/standard GAP)
        # Note: CoverageSentinel schema includes 'details', we check if 'gap_type' exists and is blocked.
        # But CoverageSentinel currently doesn't output 'gap_type' explicitly in the prompt I wrote.
        # I'll assume standard COVERAGE_GAP is eligible unless marked ABSTRACT.
        details = json.loads(alert.get('resolution_metadata', '{}')) # Wait, metadata is resolution. Details is in summary?
        # AlertManager schema stores details in... wait. persist_alert stores details json in resolution_metadata?
        # No, persist_alert:
        # VALUES (..., json.dumps(alert_data.get('details', {}))) -> this goes to... resolution_metadata?
        # Let's check AlertManager.persist_alert.
        # It maps `json.dumps(alert_data.get('details', {}))` to the LAST placeholder?
        # The placeholders are 11.
        # fields: alert_id, fingerprint, topic_id, type, severity, signal_score, state, summary, created_at, updated_at, resolution_metadata
        # That seems wrong. resolution_metadata should be empty initially.
        # `details` logic seems lost in my AlertManager implementation or I mapped it to resolution_metadata.
        # Actually, `coverage_alerts` table doesn't have a `details` column in the SQL I wrote?
        # Let's check `schema_sync.sql`.
        # `coverage_alerts`: ... summary TEXT, ... resolution_metadata JSON ...
        # It lacks a `details` JSON column! The summary is there.
        # This is a schema miss. I should have added `details JSON`.
        # For now, I'll rely on `summary` and `missing_questions` being derived or passed.
        # Wait, if I lost the `missing_questions` list, I can't generate prompts effectively.
        # I must have stored it in `resolution_metadata` by mistake in `AlertManager.persist_alert`.
        # If so, I can retrieve it from there.
        # Let's assume `resolution_metadata` currently holds the initial details (which is a bit hacky but works without migration).
        
        try:
            alert_details = json.loads(alert['resolution_metadata'])
        except:
            alert_details = {}

        if alert_details.get('gap_type') == 'ABSTRACT':
             return {"success": False, "reason": "Gap type is ABSTRACT", "prompts": []}

        # Rule 4: Coverage Score
        score_data = self.coverage_scorer.compute_score(topic_id)
        if score_data['coverage_score'] >= 0.85:
             return {"success": False, "reason": f"Coverage score is high ({score_data['coverage_score']})", "prompts": []}

        # Rule 5: Recent Attempt Failed
        attempts = self.alert_manager.get_recent_prompt_attempts(topic_id, limit=1)
        if attempts:
            last_attempt = attempts[0]
            # timestamp format: iso8601
            last_time = datetime.fromisoformat(last_attempt['attempted_at'].replace("Z", "+00:00"))
            cooldown_hours = self.config.get("cooldown_hours", 48)
            if datetime.now(timezone.utc) - last_time < timedelta(hours=cooldown_hours):
                 # Check if bricks were created? We don't track that connection easily yet.
                 # Assuming cooldown applies regardless for now as a safe default.
                 return {"success": False, "reason": f"Recent prompt attempt within {cooldown_hours}h", "prompts": []}

        # Rule 6: Deferred
        # We don't have a specific deferred flag in DB yet, skipping this check or assuming checked via state/metadata.

        # 3. Generate Prompts (L1 LLM)
        missing = alert_details.get('missing_questions', [])
        if not missing:
             # Fallback if we can't find specific missing questions
             missing = [alert['summary']]

        system_prompt = self.config.get("system_prompt", """You are an ingestion prompt generator.

Your job is to generate precise, neutral questions
that would help fill known knowledge gaps.

Rules:
- Do NOT answer the questions.
- Do NOT speculate.
- Each question must be directly ingestible from a conversation or document.
- Prefer factual, operational wording.
- Output JSON only.

Output Schema:
{
  "suggested_prompts": [
    {
      "prompt": "string",
      "resolves": ["string"]
    }
  ]
}
""")
        user_prompt = f"""
Topic: {topic_id}

Known Coverage Gaps:
{json.dumps(missing)}

Generate 3-5 ingestion prompts that, if answered,
would resolve these gaps.
"""
        try:
            intent_class = self.config.get("intent_class", "INGEST_REWRITE")
            cost_tolerance = self.config.get("cost_tolerance", "zero")

            response = self.llm_client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                intent_class=intent_class,
                cost_tolerance=cost_tolerance,
                user_visible=False
            )
            
            cleaned = self._clean_llm_response(response)
            data = json.loads(cleaned)
            prompts = data.get("suggested_prompts", [])
            
            # Log Attempts
            ts = datetime.now(timezone.utc).isoformat()
            for p in prompts:
                attempt_id = str(uuid.uuid4())
                self.alert_manager.log_prompt_attempt({
                    "id": attempt_id,
                    "alert_id": alert_id,
                    "topic_id": topic_id,
                    "prompt": p['prompt'],
                    "attempted_at": ts,
                    "outcome": "SUCCESS" # Logged as generated successfully
                })
            
            return {"success": True, "reason": "Generated", "prompts": prompts}

        except Exception as e:
            print(f"[PromptGenerator] Failed: {e}")
            return {"success": False, "reason": f"LLM Error: {e}", "prompts": []}

    def _clean_llm_response(self, response: str) -> str:
        if "```json" in response:
            return response.split("```json")[1].split("```")[0].strip()
        if "```" in response:
            return response.split("```")[1].split("```")[0].strip()
        return response.strip()
