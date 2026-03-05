import json
from typing import List, Dict, Any
from nexus.db import get_adapter
from nexus.sync.llm import LLMClient
from nexus.graph.schema import EdgeType

class L23Linker:
    """
    Generative Idea Linking Worker (L2.3).
    Discovers hidden connections between bricks using high-temperature LLM.
    """
    def __init__(self):
        self.db = get_adapter()
        self.llm = LLMClient()

    def run_discovery_cycle(self, batch_size: int = 20):
        """
        Runs one cycle of generative linking on unprocessed bricks.
        """
        print(f"[L2.3] Starting Generative Discovery cycle (batch_size: {batch_size})...")
        
        # 1. Fetch unprocessed bricks (those without 'linking_processed' tag)
        bricks = self.db.fetch_all("""
            SELECT id, data FROM graph.nodes 
            WHERE type = 'brick' AND (data->'metadata'->>'linking_processed') IS NULL
            LIMIT %s
        """, (batch_size,))
        
        if not bricks:
            print("[L2.3] No unprocessed bricks found.")
            return

        # 2. Fetch some existing context (Intents and Recent Bricks) for comparison
        intents = self.db.fetch_all("SELECT id, data FROM graph.nodes WHERE type = 'intent' LIMIT 50")
        
        context_data = {
            "intents": [
                {"id": i[0], "name": (i[1] if isinstance(i[1], dict) else json.loads(i[1])).get("name")} 
                for i in intents
            ]
        }

        # 3. Process each brick
        for b_id, b_data_raw in bricks:
            b_data = b_data_raw if isinstance(b_data_raw, dict) else json.loads(b_data_raw)
            content = b_data.get("statement") or b_data.get("content")
            
            # Generative Linking Prompt
            system_prompt = (
                "You are the Nexus Cognitive Linker (L2.3). Your goal is to find non-obvious connections between a new thought and existing projects.\n"
                "Think creatively. Connections can be functional, philosophical, or strategic.\n"
                "Output strictly JSON: {\"links\": [{\"target_id\": \"...\", \"reason\": \"...\", \"confidence\": 0.0-1.0}]}"
            )
            
            user_prompt = f"""
            New Thought: "{content}"
            
            Existing Projects (Intents):
            {json.dumps(context_data['intents'], indent=2)}
            
            Find potential links between this thought and the projects.
            """
            
            try:
                # High Temperature for creative discovery
                response_raw = self.llm.generate(
                    system_prompt, 
                    user_prompt, 
                    intent_class="DEEP_SYNTHESIS",
                    cost_tolerance="low" # Use gpt-4o-mini
                )
                
                # In this environment, llm.generate returns a stub if no API key
                # We'll parse it safely.
                if "STUB_OPENAI" in response_raw:
                    print(f"[L2.3] API STUB detected for brick {b_id}. Skipping actual edge creation.")
                else:
                    response = json.loads(response_raw)
                    for link in response.get("links", []):
                        self._create_generative_edge(b_id, link)
                
                # Mark as processed
                b_data.setdefault("metadata", {})["linking_processed"] = True
                self.db.execute(
                    "UPDATE graph.nodes SET data = %s WHERE id = %s",
                    (json.dumps(b_data), b_id)
                )
                
            except Exception as e:
                print(f"[L2.3] Error processing brick {b_id}: {e}")

    def _create_generative_edge(self, source_id: str, link: Dict[str, Any]):
        target_id = link["target_id"]
        confidence = link.get("confidence", 0.5)
        reason = link.get("reason", "Generatively discovered connection")
        
        print(f"[L2.3] Creating edge: {source_id} -> {target_id} (conf: {confidence})")
        
        metadata = {
            "discovered_by": "L2.3_Generative_Linker",
            "confidence": confidence,
            "reason": reason
        }
        
        self.db.execute("""
            INSERT INTO graph.edges (source_id, target_id, edge_type, metadata, created_at)
            VALUES (%s, %s, 'related_to', %s, NOW())
            ON CONFLICT DO NOTHING
        """, (source_id, target_id, json.dumps(metadata)))

if __name__ == "__main__":
    linker = L23Linker()
    linker.run_discovery_cycle()
