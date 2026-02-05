import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Optional
import sys

# Try to import BrickStore from Nexus
try:
    from nexus.bricks.brick_store import BrickStore
except ImportError:
    # Fallback if nexus not installed
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src")))
    from nexus.bricks.brick_store import BrickStore

class CortexAPI:
    def __init__(self, audit_log_path: str = "phase3_audit_trace.jsonl"):
        self.audit_log_path = audit_log_path
        self.brick_store = BrickStore()

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
        
        # 1.5 Inject Graph Context (GraphRAG)
        graph_context = self._fetch_graph_context(brick_ids)
        if graph_context:
            context_text += "\n\n" + graph_context
        
        # 2. LLM Call (Pluggable Backend)
        model = "gpt-4o" # Default model tag for audit
        response_text = ""
        token_cost = 0.0
        
        try:
            prompt = f"Context from memory:\n{context_text}\n\nUser: {user_query}\nAssistant:"
            
            # Check for OpenAI Key
            openai_key = os.environ.get("OPENAI_API_KEY")
            if openai_key:
                from openai import OpenAI
                client = OpenAI(api_key=openai_key)
                completion = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0
                )
                response_text = completion.choices[0].message.content
                token_cost = (completion.usage.total_tokens / 1000.0) * 0.03 # Simple estimate
            else:
                # Fallback to local Ollama if available
                import requests
                try:
                    ollama_resp = requests.post("http://localhost:11434/api/generate", json={
                        "model": "llama3",
                        "prompt": prompt,
                        "stream": False
                    }, timeout=30)
                    if ollama_resp.status_code == 200:
                        response_text = ollama_resp.json().get("response", "")
                        model = "ollama/llama3"
                    else:
                        raise Exception("Ollama returned error")
                except Exception:
                    # Final fallback for demonstration if no LLM is running
                    response_text = f"[NO LLM DETECTED] This would be a real response using the reloaded context: {context_text[:100]}..."
                    model = "mock-fallback"

        except Exception as e:
            return {"error": f"Generation failed: {str(e)}", "status": "failed"}
        
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

        # Explicitly enforce global scope for unauthenticated previews
        recalled_bricks = recall_bricks_readonly(query, allowed_scopes=["global"])

        top_bricks_output = [
            {"brick_id": brick["brick_id"], "confidence": round(brick["confidence"], 4)}
            for brick in recalled_bricks
        ]

        return {
            "query": query,
            "top_bricks": top_bricks_output,
            "status": "preview"
        }

    def assemble(self, topic: str) -> Dict:
        """Endpoint: /cognition/assemble - Trigger topic assembly"""
        print(f"[{datetime.now(timezone.utc).isoformat()}] Cortex: Assembling topic '{topic}'...")
        
        try:
            # Lazy import to avoid circular deps
            from nexus.cognition.assembler import assemble_topic
            
            artifact_path = assemble_topic(topic)
            
            # Load the artifact to return summary
            with open(artifact_path, "r", encoding="utf-8") as f:
                artifact = json.load(f)
                
            return {
                "status": "success",
                "artifact_id": artifact.get("artifact_id"),
                "path": artifact_path,
                "document_count": len(artifact.get("payload", {}).get("raw_excerpts", [])),
                "derived_from_bricks": len(artifact.get("derived_from", []))
            }
            
        except Exception as e:
            print(f"ERROR: Assembly failed: {e}")
            return {"error": str(e), "status": "failed"}

    def _reload_source_text(self, brick_ids: List[str]) -> str:
        """MODE-1 enforcement layer: Reload raw source text from bricks"""
        all_text = []
        for brick_id in brick_ids:
            text = self.brick_store.get_brick_text(brick_id)
            if text:
                all_text.append(text)
            else:
                print(f"CRITICAL: MODE-1 Violation. Failed to reload brick: {brick_id}")
                return "" # Fail fast on reload failure
        
        return "\n\n".join(all_text)

    def _fetch_graph_context(self, brick_ids: List[str]) -> str:
        """Fetch related intents/facts from the Knowledge Graph."""
        try:
            # We import here to avoid potential top-level circular deps if not using sys.path tricks
            # Ensure path is correct for import
            if "nexus" not in sys.modules:
                sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src")))
            
            from nexus.ask.recall import get_related_intents
            
            intents = get_related_intents(brick_ids)
            if not intents:
                return ""
            
            return "## Graph Context (Verified):\n" + "\n".join(f"- {i}" for i in intents)
        except Exception as e:
            print(f"WARN: Graph context fetch failed: {e}")
            return ""

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
