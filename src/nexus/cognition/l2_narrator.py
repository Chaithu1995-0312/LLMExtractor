import json
import time
from typing import Dict, Any, Optional
from nexus.cognition.persistence import CognitionLogger
from nexus.cognition.escalation_router import EscalationRouter
from nexus.cognition.confidence_engine import ConfidenceEngine

class L2Narrator:
    """
    Level 2 (L2) - The Narrator
    Role: Reactive Explanation & Contextual Narration.
    Features: 
    - Hybrid Escalation (Local -> Flash)
    - Composite Confidence Scoring
    - Budget Awareness
    """

    def __init__(self):
        self.router = EscalationRouter()
        self.confidence_engine = ConfidenceEngine()
        self.logger = CognitionLogger()

    def explain_supersession(self, old_brick: Dict, new_brick: Dict) -> str:
        """
        Explains why a new brick superseded an old one.
        Uses Hybrid Escalation Logic.
        """
        start_time = time.time()
        
        # 1. Prepare Snapshot
        snapshot = {
            "event": "SUPERCESSION",
            "old_brick_id": old_brick.get("id"),
            "old_content": old_brick.get("content"),
            "new_brick_id": new_brick.get("id"),
            "new_content": new_brick.get("content"),
            "topic_id": new_brick.get("topic_id")
        }
        snapshot_hash = self.logger.generate_snapshot_hash(snapshot)
        
        # 2. Prompts
        system_prompt = (
            "You are the Nexus Narrator (Level 2). Your job is to explain graph state transitions clearly and concisely.\n"
            "Analyze the following supersession event where a new brick replaced an old one.\n"
            "Explain strictly WHY the replacement happened based on the content difference.\n"
            "Do not hallucinate external reasons. Focus on the text evolution.\n"
            "Output JSON format: {\"explanation\": \"...\", \"confidence\": 0.0-1.0}"
        )
        
        user_prompt = f"""
        Old Content: "{old_brick.get('content')}"
        New Content: "{new_brick.get('content')}"
        
        Explain the refinement.
        """
        
        # 3. Execution (Hybrid Flow)
        
        # Attempt 1: Route via Budget Policy (Local/Tier1)
        attempt1 = self.router.route_l2(system_prompt, user_prompt)
        result1 = self._parse_response(attempt1["response"])
        
        # Compute Confidence 1
        conf1_data = self.confidence_engine.compute_l2_confidence(
            model_confidence=result1["confidence"],
            explanation=result1["explanation"],
            input_text_old=old_brick.get("content", ""),
            input_text_new=new_brick.get("content", "")
        )
        
        final_result = result1
        final_conf_data = conf1_data
        final_tier = attempt1["tier"]
        escalated = False
        
        # Check Threshold
        threshold = attempt1["threshold_target"]
        if conf1_data["final_confidence"] < threshold:
            # ESCALATION TRIGGERED
            print(f"[L2Narrator] Low confidence ({conf1_data['final_confidence']} < {threshold}). Escalating to Tier 2...")
            
            attempt2 = self.router.escalate_l2(system_prompt, user_prompt)
            result2 = self._parse_response(attempt2["response"])
            
            conf2_data = self.confidence_engine.compute_l2_confidence(
                model_confidence=result2["confidence"],
                explanation=result2["explanation"],
                input_text_old=old_brick.get("content", ""),
                input_text_new=new_brick.get("content", "")
            )
            
            # Log Attempt 1 (Failed/Low Conf)
            self._log_attempt(attempt1, result1, conf1_data, snapshot_hash, user_prompt, start_time, accepted=False)
            
            # Adopt Attempt 2
            final_result = result2
            final_conf_data = conf2_data
            final_tier = attempt2["tier"]
            escalated = True
        
        # 4. Final Logging
        self._log_attempt(
            {"tier": final_tier, "model": "Tier" + str(final_tier)}, # approximate wrapper
            final_result, 
            final_conf_data, 
            snapshot_hash, 
            user_prompt, 
            start_time, 
            accepted=True
        )
        
        return final_result["explanation"]

    def _parse_response(self, raw_response: str) -> Dict[str, Any]:
        """Parses LLM JSON response safely."""
        try:
            if "{" in raw_response:
                json_str = raw_response[raw_response.find("{"):raw_response.rfind("}")+1]
                parsed = json.loads(json_str)
                return {
                    "explanation": parsed.get("explanation", raw_response),
                    "confidence": float(parsed.get("confidence", 0.8))
                }
        except:
            pass
        return {"explanation": raw_response, "confidence": 0.8}

    def _log_attempt(self, attempt_meta, result, conf_data, snap_hash, prompt, start_time, accepted: bool):
        latency = int((time.time() - start_time) * 1000)
        
        # 1. Update usage tracking
        # Approximation: char count / 4
        tokens = (len(prompt) + len(result["explanation"])) // 4
        self.router.budget.track_usage(tokens)
        
        # 2. Persist V2 Log
        self.logger.log_insight(
            layer="L2",
            topic_id="supersession",
            trigger_event="SUPERCESSION_EXPLAINED" if accepted else "SUPERCESSION_REJECTED",
            input_snapshot_hash=snap_hash,
            prompt=prompt,
            output=result["explanation"],
            model=attempt_meta.get("model", "unknown"),
            confidence_score=conf_data["final_confidence"],
            latency_ms=latency,
            token_usage=tokens,
            confidence_components=conf_data["components"],
            threshold_used=attempt_meta.get("threshold_target"),
            escalation_tier=attempt_meta.get("tier"),
            budget_pressure=self.router.budget.get_budget_pressure()
        )
