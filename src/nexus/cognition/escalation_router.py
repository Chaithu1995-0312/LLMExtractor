from typing import Dict, Any, Optional
from nexus.sync.llm import LLMClient
from nexus.cognition.budget_controller import BudgetController
from nexus.config import get_agent_config

class EscalationRouter:
    """
    Routes cognitive requests based on budget pressure and confidence thresholds.
    Implements the Hybrid Escalation Ladder:
    Local -> Flash -> Pro (L3 only)
    """

    def __init__(self):
        self.budget = BudgetController()
        # In a real implementation, LLMClient would be more granular.
        # Here we simulate routing by passing different cost_tolerance params
        # which map to tiers in LLMClient.
        self.llm = LLMClient()
        self.config = get_agent_config("escalation_router")
        self.tiers = self.config.get("tiers", {})

    def route_l2(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """
        Executes L2 logic with budget-aware fallback.
        1. Try Tier 1 (Local/Cheap)
        2. Check Budget Threshold
        3. If fail, Escalate to Tier 2 (Flash)
        """
        # Step 1: Determine Threshold
        threshold = self.budget.get_l2_threshold()
        
        # Step 2: Attempt Tier 1 (Low Cost)
        # We use 'zero' tolerance to force local if available, or 'low' for cheapest API
        tier_config = self.tiers.get("l1_local", {})
        response = self.llm.generate(
            system_prompt, 
            user_prompt, 
            intent_class=tier_config.get("intent_class", "USER_EXPLAIN"), 
            cost_tolerance=tier_config.get("cost_tolerance", "zero")
        )
        
        # In a real system, we'd parse confidence here to decide escalation.
        # Since LLMClient returns string, we return metadata for the caller (Narrator)
        # to compute confidence and decide if a re-run is needed.
        # BUT, the Narrator needs the Router to handle the *mechanics* of escalation.
        
        # For this architecture: We return the response + metadata indicating tier.
        return {
            "response": response,
            "tier": 1,
            "model": "Local/Tier1",
            "threshold_target": threshold
        }

    def escalate_l2(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """
        Explicit escalation to Tier 2.
        """
        tier_config = self.tiers.get("l2_flash", {})
        response = self.llm.generate(
            system_prompt, 
            user_prompt, 
            intent_class=tier_config.get("intent_class", "USER_EXPLAIN"), 
            cost_tolerance=tier_config.get("cost_tolerance", "low")
        )
        return {
            "response": response,
            "tier": 2,
            "model": "Flash/Tier2",
            "threshold_target": self.budget.get_l2_threshold()
        }

    def route_l3(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """
        Executes L3 logic.
        Tier 2 (Flash) -> Tier 3 (Pro)
        """
        threshold = self.budget.get_l3_threshold()
        
        # Start at Tier 2 (Flash) for L3 tasks to save cost
        tier_config = self.tiers.get("l2_flash", {})
        response = self.llm.generate(
            system_prompt, 
            user_prompt, 
            intent_class="DEEP_SYNTHESIS", # Override L2 default for L3 routing start
            cost_tolerance=tier_config.get("cost_tolerance", "low")
        )
        
        return {
            "response": response,
            "tier": 2,
            "model": "Flash/Tier2",
            "threshold_target": threshold
        }

    def escalate_l3(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """
        Explicit escalation to Tier 3 (Pro).
        """
        tier_config = self.tiers.get("l3_pro", {})
        response = self.llm.generate(
            system_prompt, 
            user_prompt, 
            intent_class=tier_config.get("intent_class", "DEEP_SYNTHESIS"), 
            cost_tolerance=tier_config.get("cost_tolerance", "high")
        )
        
        return {
            "response": response,
            "tier": 3,
            "model": "Pro/Tier3",
            "threshold_target": self.budget.get_l3_threshold()
        }
