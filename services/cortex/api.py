import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Optional

class CortexAPI:
    def __init__(self, audit_log_path: str = "phase3_audit_trace.jsonl"):
        self.audit_log_path = audit_log_path

    def route(self, user_query: str) -> Dict:
        """Endpoint: /route - Intent-based routing (LOCKED Rules)"""
        query_lower = user_query.lower()
        
        # Deterministic Routing Table
        if any(word in query_lower for word in ["trade", "market", "stock", "price"]):
            return {"agent_id": "Jarvis", "model": "Claude"}
        
        if any(word in query_lower for word in ["architect", "code", "implement", "design"]):
            return {"agent_id": "Architect", "model": "Gemini"}
            
        if any(word in query_lower for word in ["research", "find", "who", "when"]):
            return {"agent_id": "ResearchPro", "model": "Gemini"}
            
        if any(word in query_lower for word in ["video", "creative", "story", "write"]):
            return {"agent_id": "VideoFactory", "model": "GPT"}
            
        # Default fallback
        return {"agent_id": "General", "model": "GPT"}

    def generate(self, user_id: str, agent_id: str, user_query: str, brick_ids: List[str]) -> Dict:
        """Endpoint: /generate - Secure generation with memory injection"""
        print(f"[{datetime.now(timezone.utc).isoformat()}] Cortex: Generating response for {agent_id}...")
        
        # 1. Inject memory (Reload raw source)
        context_text = self._reload_source_text(brick_ids)
        if not context_text and brick_ids:
            return {"error": "MODE-1 Violation: Source reload failed.", "status": "blocked"}
        
        # 2. LLM Call (Mock for skeleton)
        model = "gpt-4o" # Example
        response_text = f"Simulated response for: {user_query[:20]}..."
        token_cost = 0.002 # Mock
        
        # 3. Emit audit record
        self._audit_trace(user_id, agent_id, brick_ids, model, token_cost)
        
        return {
            "response": response_text,
            "model": model,
            "status": "success"
        }

    def ask_preview(self, query: str) -> Dict:
        # This method is for Jarvis UI read-only preview.
        # It MUST NOT call self.generate() or emit audit rows.
        
        # Import the read-only recall adapter for Cortex
        # This import is done locally to avoid circular dependencies if api.py is imported elsewhere
        # and to emphasize that Cortex is calling out to Nexus for recall, not performing it itself.
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "nexus-cli")))
        from nexus.ask.recall import recall_bricks_readonly

        recalled_bricks = recall_bricks_readonly(query)

        top_bricks_output = [
            {"brick_id": brick["brick_id"], "confidence": round(brick["confidence"], 4)}
            for brick in recalled_bricks
        ]

        return {
            "query": query,
            "top_bricks": top_bricks_output,
            "status": "preview"
        }


    def _reload_source_text(self, brick_ids: List[str]) -> str:
        """MODE-1 enforcement layer: Reload raw source text from bricks"""
        all_text = []
        for brick_id in brick_ids:
            # In a real implementation, we would look up the brick_id 
            # in a mapping and reload from tree files.
            # Mocking the lookup and reload logic.
            print(f"Reloading raw source for brick: {brick_id}")
            # If reload fails -> BLOCK (return empty/None)
            all_text.append(f"Content for {brick_id}")
        
        return "\n".join(all_text)

    def _audit_trace(self, user_id: str, agent_id: str, brick_ids: List[str], model: str, token_cost: float):
        """Mandatory audit logging"""
        record = {
            "user_id": user_id,
            "agent_id": agent_id,
            "brick_ids_used": brick_ids,
            "model": model,
            "token_cost": token_cost,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        with open(self.audit_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
