import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Optional
import sys
import numpy as np

# Try to import BrickStore from Nexus
try:
    from nexus.bricks.brick_store import BrickStore
    from nexus.vector.embedder import get_embedder
except ImportError:
    # Fallback if nexus not installed
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src")))
    from nexus.bricks.brick_store import BrickStore
    from nexus.vector.embedder import get_embedder

# Flexible import for JarvisGateway (handles root vs services/ path context)
try:
    from services.cortex.gateway import JarvisGateway
except ImportError:
    try:
        from cortex.gateway import JarvisGateway
    except ImportError:
        # Fallback to relative import if package structure allows
        from .gateway import JarvisGateway

from nexus.graph.prompt_manager import PromptManager

class CortexAPI:
    def __init__(self, audit_log_path: str = "phase3_audit_trace.jsonl"):
        self.audit_log_path = audit_log_path
        self.brick_store = BrickStore()
        # Initialize the Multi-Tier Gateway
        self.gateway = JarvisGateway()
        
        self.agent_profiles = {
            "Jarvis": "Expert in financial markets, trading, stocks, and economic analysis.",
            "Architect": "Expert in software architecture, code implementation, design patterns, and system engineering.",
            "ResearchPro": "Expert in deep research, finding facts, historical data, and answering 'who/when' questions.",
            "VideoFactory": "Expert in creative writing, video production, storytelling, and content creation.",
            "General": "General purpose assistant for casual conversation and broad queries."
        }
        self.agent_embeddings = {}
        self._init_agent_embeddings()

    def _init_agent_embeddings(self):
        try:
            embedder = get_embedder()
            for agent_id, desc in self.agent_profiles.items():
                self.agent_embeddings[agent_id] = embedder.embed_query(desc)
            print("[CortexAPI] Semantic routing initialized.")
        except Exception as e:
            print(f"[CortexAPI] Failed to initialize semantic routing: {e}")

    def route(self, user_query: str) -> Dict:
        """Endpoint: /route - Intent-based routing (Semantic + Fallback)"""
        try:
            embedder = get_embedder()
            query_vec = embedder.embed_query(user_query)
            
            best_agent = "General"
            best_score = -1.0
            
            for agent_id, agent_vec in self.agent_embeddings.items():
                # Cosine similarity
                score = np.dot(query_vec.flatten(), agent_vec.flatten()) / (np.linalg.norm(query_vec) * np.linalg.norm(agent_vec))
                if score > best_score:
                    best_score = score
                    best_agent = agent_id
            
            # Threshold for fallback
            if best_score < 0.2:
                best_agent = "General"
                
            model_map = {
                "Jarvis": "Claude",
                "Architect": "Gemini",
                "ResearchPro": "Gemini",
                "VideoFactory": "GPT",
                "General": "GPT"
            }
            
            return {"agent_id": best_agent, "model": model_map.get(best_agent, "GPT"), "confidence": float(best_score)}
            
        except Exception as e:
            print(f"[CortexAPI] Semantic routing failed, using fallback: {e}")
            # Fallback to keyword routing
            query_lower = user_query.lower()
            if any(word in query_lower for word in ["trade", "market", "stock", "price"]):
                return {"agent_id": "Jarvis", "model": "Claude"}
            if any(word in query_lower for word in ["architect", "code", "implement", "design"]):
                return {"agent_id": "Architect", "model": "Gemini"}
            if any(word in query_lower for word in ["research", "find", "who", "when"]):
                return {"agent_id": "ResearchPro", "model": "Gemini"}
            if any(word in query_lower for word in ["video", "creative", "story", "write"]):
                return {"agent_id": "VideoFactory", "model": "GPT"}
            return {"agent_id": "General", "model": "GPT"}

    def generate(self, user_id: str, agent_id: str, user_query: str, brick_ids: List[str]) -> Dict:
        """Endpoint: /generate - Now uses Tier 2 (The Voice)"""
        print(f"[{datetime.now(timezone.utc).isoformat()}] Cortex: Generating response for {agent_id}...")
        
        # 1. Inject Memory (Same as before)
        context_text = self._reload_source_text(brick_ids)
        if not context_text and brick_ids: # Keep original logic: fail if bricks requested but reload failed
             return {"error": "MODE-1 Violation: Source reload failed.", "status": "blocked"}

        # 1.5 Inject Graph Context (GraphRAG)
        graph_context = self._fetch_graph_context(brick_ids)
        if graph_context:
            context_text += "\n\n" + graph_context

        # 2. Call Gateway (Tier 2)
        # This routes to Claude-3.5 via LiteLLM and checks budget
        result = self.gateway.explain(user_query, context_text)
        
        if "error" in result:
            # Handle Budget Cap Gracefully
            if result["error"] == "DAILY_BUDGET_EXCEEDED":
                return {
                    "response": "⚠️ **SYSTEM ALERT**: Daily cognitive budget depleted. Operating in Read-Only Mode.",
                    "status": "budget_locked"
                }
            return {"response": f"Cognitive Failure: {result['content']}", "status": "failed"}

        # 3. Audit (Now includes accurate usage data from proxy)
        usage = result.get("usage", {})
        # Estimate cost (blended rate for Sonnet) -> ~$3.00 / 1M input + $15 / 1M output
        # Rough calc: (Input * 3e-6) + (Output * 15e-6)
        est_cost = (usage.get("prompt_tokens", 0) * 0.000003) + (usage.get("completion_tokens", 0) * 0.000015)
        
        self._audit_trace(user_id, agent_id, brick_ids, "jarvis-l2", est_cost)
        
        return {
            "response": result["content"],
            "model": "jarvis-l2",
            "usage": usage,
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

    def synthesize(self, topic_id: Optional[str] = None) -> Dict:
        """Endpoint: /cognition/synthesize - Trigger relationship discovery"""
        print(f"[{datetime.now(timezone.utc).isoformat()}] Cortex: Synthesizing relationships (topic={topic_id})...")
        
        try:
            from nexus.cognition.synthesizer import run_relationship_synthesis
            
            discovered_count = run_relationship_synthesis(topic_id=topic_id)
            
            return {
                "status": "success",
                "discovered_relationships": discovered_count,
                "topic_id": topic_id
            }
        except Exception as e:
            print(f"ERROR: Synthesis failed: {e}")
            return {"error": str(e), "status": "failed"}

    def calculate_complexity_score(self, content: str) -> float:
        """Calculate a complexity score based on structure, directives, and density."""
        if not content or not isinstance(content, str):
            return 0.0
            
        score = 0.0
        
        # 1. Structural Markers (Markdown)
        score += content.count("#") * 5.0  # Headers
        score += content.count("---") * 10.0  # Dividers
        score += content.count("===") * 10.0  # Dividers
        score += content.count("**") * 2.0   # Bold markers
        score += content.count("- ") * 1.5   # List items
        score += content.count("1. ") * 2.0  # Numbered items
        
        # 2. Semantic Markers (Directives & Roles)
        directives = ["MUST", "STRICT", "REQUIREMENTS", "RULE", "FAIL", "QUALITY", "CORE", "DIRECTIVE"]
        for d in directives:
            if d in content:
                score += 15.0
                
        roles = ["Architect", "Psychologist", "Linguist", "Analyst", "Synthesizer", "Engineer"]
        for r in roles:
            if r.lower() in content.lower():
                score += 10.0
                
        # 3. Text Density & Variation
        lines = content.split("\n")
        score += len(lines) * 1.0  # Length bonus
        
        # Unique word density
        words = content.lower().split()
        if len(words) > 0:
            unique_ratio = len(set(words)) / len(words)
            score += unique_ratio * 20.0
            
        return min(round(score, 2), 1000.0) # Cap for normalization if needed

    def get_audit_events(self, limit: int = 100, offset: int = 0, event_type: Optional[str] = None, component: Optional[str] = None, run_id: Optional[str] = None) -> Dict:
        """Endpoint: /api/audit/events - Standardized observability stream"""
        events = []
        try:
            if os.path.exists(self.audit_log_path):
                with open(self.audit_log_path, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            evt = json.loads(line)
                            # Filters
                            if event_type and evt.get("event") != event_type: continue
                            if component and evt.get("component") != component: continue
                            if run_id and evt.get("run_id") != run_id: continue
                            events.append(evt)
                        except: continue
            
            # Sort DESC
            events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            total = len(events)
            return {
                "events": events[offset:offset+limit],
                "total": total
            }
        except Exception as e:
            return {"events": [], "total": 0, "error": str(e)}

    def get_run_details(self, run_id: str) -> Dict:
        """Endpoint: /api/runs/{run_id} - Run Inspector data"""
        try:
            from nexus.sync.db import SyncDatabase
            db = SyncDatabase()
            run = db.get_run(run_id)
            if not run:
                return {"error": "Run not found"}
            
            content = run["raw_content"]
            total_msgs = len(content.get("messages", [])) if isinstance(content, dict) else 0
            
            # Aggregate stats from audit log
            stats = {"llm_calls_executed": 0, "llm_calls_skipped": 0, "bricks_created": 0}
            if os.path.exists(self.audit_log_path):
                with open(self.audit_log_path, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            evt = json.loads(line)
                            if evt.get("run_id") == run_id:
                                if evt.get("event") == "LLM_CALL_EXECUTED": stats["llm_calls_executed"] += 1
                                elif evt.get("event") == "LLM_CALL_SKIPPED": stats["llm_calls_skipped"] += 1
                                elif evt.get("event") == "BRICK_MATERIALIZED": stats["bricks_created"] += 1
                        except: continue

            return {
                "run_id": run_id,
                "total_messages": total_msgs,
                "last_processed_index": run.get("last_processed_index", -1),
                "new_messages": max(0, total_msgs - (run.get("last_processed_index", -1) + 1)),
                "stats": stats
            }
        except Exception as e:
            return {"error": str(e)}

    def get_graph_snapshot(self) -> Dict:
        """Endpoint: /api/graph/snapshot - Read-only wall view"""
        try:
            from nexus.graph.manager import GraphManager
            gm = GraphManager()
            return {
                "nodes": gm.get_all_nodes_raw(),
                "edges": gm.get_all_edges_raw()
            }
        except Exception as e:
            return {"error": str(e)}

    def get_all_prompts(self, min_score: float = 0.0) -> List[Dict]:
        """Crawl output/nexus/trees/ and return all user/assistant messages + system prompts."""
        prompts = []
        
        # 1. System Prompts (Governance)
        try:
            pm = PromptManager()
            system_prompts = pm.get_all_system_prompts()
            for sp in system_prompts:
                meta = json.loads(sp['metadata']) if sp['metadata'] else {}
                prompts.append({
                    "conversation_id": "GOVERNANCE",
                    "title": f"System Prompt: {sp['slug']}",
                    "message_id": f"{sp['slug']}_v{sp['version']}",
                    "role": sp['role'],
                    "content": sp['content'],
                    "model_name": meta.get('model', 'governance'),
                    "created_at": sp['created_at'],
                    "complexity_score": self.calculate_complexity_score(sp['content'])
                })
        except Exception as e:
            print(f"WARN: Failed to fetch system prompts: {e}")

        # 2. Trace Trees (Historical)
        # Relative to project root
        trees_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "output", "nexus", "trees"))
        
        if not os.path.exists(trees_dir):
            return []

        for root, _, files in os.walk(trees_dir):
            for file in files:
                if file.endswith(".json"):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            
                        conv_id = data.get("conversation_id")
                        title = data.get("title")
                        
                        for msg in data.get("messages", []):
                            role = msg.get("role")
                            if role in ["user", "assistant"]:
                                content = msg.get("content", "")
                                if not content: continue
                                
                                score = self.calculate_complexity_score(content)
                                if score >= min_score:
                                    prompts.append({
                                        "conversation_id": conv_id,
                                        "title": title,
                                        "message_id": msg.get("message_id"),
                                        "role": role,
                                        "content": content,
                                        "model_name": msg.get("model_name"),
                                        "created_at": msg.get("created_at"),
                                        "complexity_score": score
                                    })
                    except Exception as e:
                        print(f"WARN: Failed to read tree file {file_path}: {e}")
        
        # Sort by complexity score (highest first) then timestamp
        prompts.sort(key=lambda x: (x.get("complexity_score", 0), x.get("created_at") or ""), reverse=True)
        return prompts

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
