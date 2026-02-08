import os
import json
import requests
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import sys

# Add src to path for nexus imports
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src")))

from nexus.graph.prompt_manager import PromptManager

class JarvisGateway:
    """
    The Cognitive Router.
    Decides whether to use the 'Lizard Brain' (Local/Free) or 'Wizard Brain' (Cloud/Paid).
    Enforces the $2.00/day budget via the LiteLLM Proxy.
    """
    
    def __init__(self, local_url="http://localhost:11434", proxy_url="http://0.0.0.0:4000"):
        self.local_url = local_url
        self.proxy_url = proxy_url
        self.local_model = "llama3"  # or "mistral"
        self.prompt_manager = PromptManager()
        
    def pulse(self, event_type: str, context: Dict) -> str:
        """
        TIER L1: The Pulse (Cost: $0.00)
        Used for: Status updates, simple narration, log summarization.
        Routing: Local Ollama instance.
        """
        fallback_prompt = f"""
        [ROLE] You are the Nexus System Narrator.
        [TASK] Summarize this system event in one sentence (<15 words).
        [TONE] Clinical, objective, cybernetic.
        [EVENT] {event_type}: {json.dumps(context)}
        """
        
        try:
            # Governance-checked prompt
            raw_prompt = self.prompt_manager.get_prompt("jarvis-l1-pulse", fallback=fallback_prompt)
            # Re-inject variables if they were placeholders in DB
            prompt = raw_prompt.replace("{event_type}", event_type).replace("{context}", json.dumps(context))

            # Try Local First
            payload = {
                "model": self.local_model,
                "prompt": prompt,
                "stream": False
            }
            resp = requests.post(f"{self.local_url}/api/generate", json=payload, timeout=2)
            if resp.status_code == 200:
                return resp.json().get("response", "").strip()
            
        except Exception as e:
            print(f"[Jarvis] L1 Pulse Failed (Local): {e}")
            
        # Fallback: Deterministic string (Do NOT spend money on this)
        return f"System event {event_type} processed successfully."

    def explain(self, query: str, context_bricks: str) -> Dict:
        """
        TIER L2: The Voice (Cost: ~$0.01/call)
        Used for: "Why" questions, conflict resolution, intent analysis.
        Routing: LiteLLM Proxy (Claude-3.5-Sonnet).
        """
        fallback_system = """
        You are Jarvis, the Governor of the Nexus State.
        1. Answer based ONLY on the provided Brick context.
        2. If the bricks contradict, highlight the conflict.
        3. Never invent facts not in the context.
        """
        
        system_msg = self.prompt_manager.get_prompt("jarvis-l2-system", fallback=fallback_system)

        payload = {
            "model": "jarvis-l2", # Maps to Claude-3.5 via Proxy
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": f"CONTEXT:\n{context_bricks}\n\nQUERY: {query}"}
            ]
        }
        
        return self._call_proxy(payload)

    def synthesize(self, topic_data: str) -> Dict:
        """
        TIER L3: The Sage (Cost: ~$0.15/call)
        Used for: Deep architectural reviews, monthly audits.
        Routing: LiteLLM Proxy (o1-preview or GPT-4o).
        """
        payload = {
            "model": "jarvis-l3", # Maps to o1/GPT-4o via Proxy
            "messages": [
                {"role": "user", "content": f"Perform a deep structural analysis of this topic:\n{topic_data}"}
            ]
        }
        return self._call_proxy(payload)

    def _call_proxy(self, payload: Dict) -> Dict:
        """Helper to hit the budget-gated proxy."""
        try:
            resp = requests.post(
                f"{self.proxy_url}/chat/completions", 
                json=payload, 
                headers={"Authorization": "Bearer sk-1234"} # Matches config.yaml
            )
            
            if resp.status_code == 429:
                return {"error": "DAILY_BUDGET_EXCEEDED", "content": "Critical: Daily cognitive budget ($2.00) depleted."}
                
            if resp.status_code == 200:
                data = resp.json()
                content = data['choices'][0]['message']['content']
                usage = data.get('usage', {})
                return {"content": content, "usage": usage}
                
            return {"error": f"Proxy Error {resp.status_code}", "content": resp.text}
            
        except Exception as e:
            return {"error": "CONNECTION_FAILED", "content": str(e)}
