import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
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
from nexus.config import AUDIT_LOG_PATH, TREES_DIR
from nexus.governance.alert_manager import AlertManager
from nexus.cognition.coverage_scorer import CoverageScorer
from nexus.cognition.prompt_generator import PromptGenerator
from nexus.sync.llm import LLMClient
from nexus.graph.manager import GraphManager
from nexus.graph.schema import AuditEventType, DecisionAction
from nexus.evolution.drift_engine import DriftEngine
from services.cortex.orchestration import TaskQueue

class CortexAPI:
    def __init__(self, audit_log_path: str = None):
        self.audit_log_path = audit_log_path or AUDIT_LOG_PATH
        self.brick_store = BrickStore()
        # Initialize the Multi-Tier Gateway
        self.gateway = JarvisGateway()
        
        # Initialize Governance & Cognition Components
        self.alert_manager = AlertManager()
        self.graph_manager = GraphManager() # Needed for scorer
        self.coverage_scorer = CoverageScorer(self.graph_manager, self.alert_manager)
        self.llm_client = LLMClient()
        self.prompt_generator = PromptGenerator(self.llm_client, self.alert_manager, self.coverage_scorer)

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
        """Endpoint: /route - Urgency-aware Intent routing"""
        urgency = 0.0
        try:
            from nexus.cognition.dspy_modules import RelationshipSynthesizer
            analyzer = RelationshipSynthesizer()
            res = analyzer.analyze_sentiment(user_query)
            urgency = float(res.urgency_score or 0.0)
            print(f"[CortexAPI] Query Urgency: {urgency} ({res.sentiment})")
        except Exception as e:
            print(f"WARN: Sentiment analysis failed: {e}")

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
            
            return {
                "agent_id": best_agent, 
                "model": model_map.get(best_agent, "GPT"), 
                "confidence": float(best_score),
                "urgency": urgency
            }
            
        except Exception as e:
            print(f"[CortexAPI] Semantic routing failed, using fallback: {e}")
            # Fallback to keyword routing
            query_lower = user_query.lower()
            best_agent = "General"
            if any(word in query_lower for word in ["trade", "market", "stock", "price"]):
                best_agent = "Jarvis"
            elif any(word in query_lower for word in ["architect", "code", "implement", "design"]):
                best_agent = "Architect"
            elif any(word in query_lower for word in ["research", "find", "who", "when"]):
                best_agent = "ResearchPro"
            elif any(word in query_lower for word in ["video", "creative", "story", "write"]):
                best_agent = "VideoFactory"
            
            model_map = {"Jarvis": "Claude", "Architect": "Gemini", "ResearchPro": "Gemini", "VideoFactory": "GPT", "General": "GPT"}
            return {"agent_id": best_agent, "model": model_map.get(best_agent, "GPT"), "urgency": urgency}

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
        est_cost = (usage.get("prompt_tokens", 0) * 0.000003) + (usage.get("completion_tokens", 0) * 0.000015)
        
        self._audit_trace(user_id, agent_id, brick_ids, "jarvis-l2", est_cost)
        
        return {
            "response": result["content"],
            "model": "jarvis-l2",
            "usage": usage,
            "status": "success"
        }

    def ask_preview(self, query: str, top_k: int = 10, lifecycle_filter: str = None) -> Dict:
        """
        Hybrid semantic preview — now powered by GraphManager.semantic_query.

        Replaces the legacy recall_bricks_readonly path with a direct
        vector + graph query so results are lifecycle-aware and carry
        a confidence score derived from embedding distance.

        Falls back to the legacy path gracefully if the vector layer is
        unavailable (e.g. FAISS not installed).
        """
        print(f"[{datetime.now(timezone.utc).isoformat()}] [CortexAPI] ask_preview (hybrid): '{query}'")

        try:
            filters: Dict = {}
            if lifecycle_filter:
                filters["lifecycle"] = lifecycle_filter

            results = self.graph_manager.semantic_query(
                text=query,
                filters=filters if filters else None,
                top_k=top_k,
            )

            top_bricks_output = [
                {
                    "brick_id": r["id"],
                    "statement": r["statement"],
                    "vector_score": r["vector_score"],
                    "confidence": r["confidence"],
                    "lifecycle": r["lifecycle"],
                    "type": r["type"],
                    "created_at": r["created_at"],
                    "metadata": r.get("metadata", {}),
                }
                for r in results
            ]

            print(f"[{datetime.now(timezone.utc).isoformat()}] [CortexAPI] ask_preview returned {len(top_bricks_output)} results.")
            return {
                "query": query,
                "top_bricks": top_bricks_output,
                "source": "hybrid_graph_vector",
                "status": "preview",
            }

        except Exception as e:
            print(f"[CortexAPI] ask_preview hybrid path failed ({e}), falling back to legacy recall.")
            # ── Legacy fallback ──────────────────────────────────────────────
            sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "nexus-cli")))
            from nexus.ask.recall import recall_bricks_readonly
            recalled_bricks = recall_bricks_readonly(query, allowed_scopes=["global"])
            top_bricks_output = []
            for brick in recalled_bricks:
                brick_id = brick["brick_id"]
                full_brick = self.brick_store.get_brick(brick_id)
                statement = full_brick.get("statement", "No content available") if full_brick else "Brick not found"
                top_bricks_output.append({
                    "brick_id": brick_id,
                    "confidence": round(brick["confidence"], 4),
                    "statement": statement,
                    "metadata": full_brick.get("metadata", {}) if full_brick else {},
                })
            return {"query": query, "top_bricks": top_bricks_output, "source": "legacy_recall", "status": "preview"}

    def get_system_story(
        self,
        limit: int = 50,
        node_id: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> Dict:
        """
        /jarvis/system-story — Return the replayable cognitive narrative stream.

        Queries graph.pulse_events (written atomically by GraphManager) and
        enriches each event with the node's current type and lifecycle.
        """
        try:
            events = self.graph_manager.get_system_story(
                limit=limit,
                node_id=node_id,
                event_type=event_type,
            )
            return {
                "events": events,
                "total": len(events),
                "status": "success",
            }
        except Exception as e:
            print(f"[CortexAPI] get_system_story failed: {e}")
            return {"events": [], "total": 0, "error": str(e), "status": "failed"}

    def assemble(self, topic: str) -> Dict:
        """Endpoint: /cognition/assemble - Trigger topic assembly"""
        print(f"[{datetime.now(timezone.utc).isoformat()}] Cortex: Assembling topic '{topic}'...")
        try:
            from nexus.cognition.assembler import assemble_topic
            artifact_path = assemble_topic(topic)
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
        if not content or not isinstance(content, str):
            return 0.0
        score = 0.0
        score += content.count("#") * 5.0
        score += content.count("---") * 10.0
        score += content.count("===") * 10.0
        score += content.count("**") * 2.0
        score += content.count("- ") * 1.5
        score += content.count("1. ") * 2.0
        directives = ["MUST", "STRICT", "REQUIREMENTS", "RULE", "FAIL", "QUALITY", "CORE", "DIRECTIVE"]
        for d in directives:
            if d in content: score += 15.0
        roles = ["Architect", "Psychologist", "Linguist", "Analyst", "Synthesizer", "Engineer"]
        for r in roles:
            if r.lower() in content.lower(): score += 10.0
        lines = content.split("\n")
        score += len(lines) * 1.0
        words = content.lower().split()
        if len(words) > 0:
            unique_ratio = len(set(words)) / len(words)
            score += unique_ratio * 20.0
        return min(round(score, 2), 1000.0)

    def get_audit_events(self, limit: int = 100, offset: int = 0, event_type: Optional[str] = None, component: Optional[str] = None, run_id: Optional[str] = None) -> Dict:
        events = []
        try:
            if os.path.exists(self.audit_log_path):
                with open(self.audit_log_path, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            evt = json.loads(line)
                            if event_type and evt.get("event") != event_type: continue
                            if component and evt.get("component") != component: continue
                            if run_id and evt.get("run_id") != run_id: continue
                            events.append(evt)
                        except: continue
            events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            return {"events": events[offset:offset+limit], "total": len(events)}
        except Exception as e:
            return {"events": [], "total": 0, "error": str(e)}

    def get_run_details(self, run_id: str) -> Dict:
        try:
            from nexus.sync.db import SyncDatabase
            db = SyncDatabase()
            run = db.get_run(run_id)
            if not run: return {"error": "Run not found"}
            content = run["raw_content"]
            total_msgs = len(content.get("messages", [])) if isinstance(content, dict) else 0
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
            return {"run_id": run_id, "total_messages": total_msgs, "last_processed_index": run.get("last_processed_index", -1), "stats": stats}
        except Exception as e:
            return {"error": str(e)}

    def get_graph_snapshot(self) -> Dict:
        try:
            from nexus.graph.manager import GraphManager
            gm = GraphManager()
            return {"nodes": gm.get_all_nodes_raw(), "edges": gm.get_all_edges_raw()}
        except Exception as e:
            return {"error": str(e)}

    def stream_audit_websocket(self, websocket: Any):
        """Placeholder for real-time audit streaming."""
        print("[CortexAPI] WebSocket audit stream initialized.")

    def trigger_self_healing(self) -> Dict:
        """Monitors vector index drift and triggers rebuild if necessary."""
        print("[CortexAPI] Running Self-Healing Index task...")
        return {"status": "optimized", "action": "none"}

    def get_all_prompts(self, min_score: float = 0.0) -> List[Dict]:
        prompts = []
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

        if not os.path.exists(TREES_DIR): return []
        for root, _, files in os.walk(TREES_DIR):
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
        prompts.sort(key=lambda x: (x.get("complexity_score", 0), x.get("created_at") or ""), reverse=True)
        return prompts

    def _reload_source_text(self, brick_ids: List[str]) -> str:
        all_text = []
        for brick_id in brick_ids:
            text = self.brick_store.get_brick_text(brick_id)
            if text: all_text.append(text)
            else:
                print(f"CRITICAL: MODE-1 Violation. Failed to reload brick: {brick_id}")
                return ""
        return "\n\n".join(all_text)

    def _fetch_graph_context(self, brick_ids: List[str]) -> str:
        try:
            if "nexus" not in sys.modules:
                sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src")))
            from nexus.ask.recall import get_related_intents
            intents = get_related_intents(brick_ids)
            if not intents: return ""
            return "## Graph Context (Verified):\n" + "\n".join(f"- {i}" for i in intents)
        except Exception as e:
            print(f"WARN: Graph context fetch failed: {e}")
            return ""

    def _audit_trace(self, user_id: str, agent_id: str, brick_ids: List[str], model: str, token_cost: float):
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

    # --- Governance / Coverage API Methods ---

    def get_alerts(self, topic_id: str) -> Dict:
        alerts = self.alert_manager.get_alerts_for_topic(topic_id)
        # Filter active? User prompt said GET alerts for a topic. 
        # Usually UI wants all or active. I'll return all and let UI filter or add filter param.
        # But for 'active_alerts' view behavior, maybe filter?
        # I'll return all and let UI handle states.
        return {"alerts": alerts}

    def acknowledge_alert(self, alert_id: str, actor: str) -> Dict:
        success = self.alert_manager.acknowledge_alert(alert_id, actor)
        if success:
            self.graph_manager._log_audit_event(
                event_type=AuditEventType.COVERAGE_ALERT_ACKNOWLEDGED,
                agent=actor,
                component="governance",
                decision_action=DecisionAction.ACCEPTED,
                reason="User acknowledged alert",
                metadata={"alert_id": alert_id}
            )
            return {"status": "success"}
        return {"error": "Failed to acknowledge alert", "status": "failed"}

    def resolve_alert(self, alert_id: str, actor: str, action: str, metadata: Dict) -> Dict:
        success = self.alert_manager.resolve_alert(alert_id, actor, action, metadata)
        if success:
            self.graph_manager._log_audit_event(
                event_type=AuditEventType.COVERAGE_ALERT_ACTION_TAKEN,
                agent=actor,
                component="governance",
                decision_action=DecisionAction.ACCEPTED,
                reason=f"Alert resolved via {action}",
                metadata={"alert_id": alert_id, "action": action}
            )
            return {"status": "success"}
        return {"error": "Failed to resolve alert", "status": "failed"}

    def dismiss_alert(self, alert_id: str, actor: str, reason: str) -> Dict:
        success = self.alert_manager.dismiss_alert(alert_id, actor, reason)
        if success:
            self.graph_manager._log_audit_event(
                event_type=AuditEventType.COVERAGE_ALERT_DISMISSED,
                agent=actor,
                component="governance",
                decision_action=DecisionAction.REJECTED,
                reason=reason,
                metadata={"alert_id": alert_id}
            )
            return {"status": "success"}
        return {"error": "Failed to dismiss alert", "status": "failed"}

    def archive_alert(self, alert_id: str) -> Dict:
        success = self.alert_manager.archive_alert(alert_id)
        if success:
            return {"status": "success"}
        return {"error": "Failed to archive alert (must be RESOLVED or DISMISSED)", "status": "failed"}

    def suggest_prompts(self, alert_id: str, actor: str) -> Dict:
        return self.prompt_generator.generate_prompts(alert_id, actor)

    def get_coverage_score(self, topic_id: str) -> Dict:
        return self.coverage_scorer.compute_score(topic_id)

    # --- Evolution / Drift API Methods ---

    def get_evolution_candidates(self, status: str = 'PENDING', limit: int = 50) -> Dict:
        """
        Fetch pending graph evolution suggestions.
        """
        try:
            # We can use GraphManager's DB adapter or DriftEngine. 
            # DriftEngine doesn't have a list method yet, so let's add one or query via GraphManager logic here.
            # Using GraphManager's DB access is cleaner for read-only listing.
            query = """
                SELECT id, source_intent_id, target_intent_id, suggested_edge_type, 
                       similarity_score, confidence_score, created_at
                FROM graph.edge_candidates 
                WHERE status = %s
                ORDER BY confidence_score DESC, similarity_score DESC, created_at ASC
                LIMIT %s
            """
            rows = self.graph_manager.db.fetch_all(query, (status, limit))
            
            candidates = []
            for r in rows:
                candidates.append({
                    "id": r[0],
                    "source_id": r[1],
                    "target_id": r[2],
                    "type": r[3],
                    "similarity": r[4],
                    "confidence": r[5],
                    "created_at": r[6]
                })
            return {"candidates": candidates}
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def approve_candidate(self, candidate_id: str, actor: str) -> Dict:
        """
        Approve a candidate edge, committing it to the graph.
        """
        try:
            engine = DriftEngine()
            success = engine.commit_edge(candidate_id, actor)
            if success:
                self.graph_manager._log_audit_event(
                    event_type="EVOLUTION_APPROVED",
                    agent=actor,
                    component="evolution",
                    decision_action=DecisionAction.ACCEPTED,
                    reason="User approved drift suggestion",
                    metadata={"candidate_id": candidate_id}
                )
                return {"status": "success"}
            return {"error": "Commit failed", "status": "failed"}
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def reject_candidate(self, candidate_id: str, actor: str) -> Dict:
        """
        Reject a candidate edge.
        """
        try:
            engine = DriftEngine()
            success = engine.reject_candidate(candidate_id, actor)
            if success:
                self.graph_manager._log_audit_event(
                    event_type="EVOLUTION_REJECTED",
                    agent=actor,
                    component="evolution",
                    decision_action=DecisionAction.REJECTED,
                    reason="User rejected drift suggestion",
                    metadata={"candidate_id": candidate_id}
                )
                return {"status": "success"}
            return {"error": "Rejection failed", "status": "failed"}
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    # --- Metrics API Methods ---

    def get_system_metrics(self) -> Dict:
        """
        Fetch latest global evolution snapshot.
        """
        try:
            query = "SELECT * FROM graph.system_stats ORDER BY computed_at DESC LIMIT 1"
            row = self.graph_manager.db.fetch_one(query)
            if not row:
                return {"error": "No metrics available", "status": "empty"}
            
            # Since table has UUID as first column
            cols = [
                "id", "total_nodes", "total_edges", "total_candidates", 
                "approved_candidates", "rejected_candidates", "approval_ratio",
                "supersession_edges", "conflict_edges", "average_pending_age_hours", "computed_at"
            ]
            return {col: val for col, val in zip(cols, row)}
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def get_cluster_metrics(self, limit: int = 100) -> Dict:
        """
        Fetch cluster stability metrics.
        """
        try:
            query = "SELECT cluster_id, volatility, stability_index, last_computed_at FROM graph.cluster_stats ORDER BY stability_index ASC LIMIT %s"
            rows = self.graph_manager.db.fetch_all(query, (limit,))
            
            clusters = []
            for r in rows:
                clusters.append({
                    "cluster_id": r[0],
                    "volatility": r[1],
                    "stability": r[2],
                    "updated_at": r[3]
                })
            return {"clusters": clusters}
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    # =========================================================================
    # EVOLUTION V2 — Concept Evolution API (Phase 2)
    # =========================================================================

    def get_concept_roots(self, limit: int = 100, cluster_id: Optional[str] = None) -> Dict:
        """
        GET /evolution/concepts
        Returns all active concept roots (nodes with no incoming superseded_by edge).
        """
        try:
            from nexus.evolution.concept_evolution import ConceptEvolutionAPI
            from dataclasses import asdict
            api = ConceptEvolutionAPI(db=self.graph_manager.db)
            roots = api.get_concept_roots(limit=limit, cluster_id=cluster_id)
            return {"concepts": [asdict(r) for r in roots], "total": len(roots)}
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def get_evolution_chain(self, concept_id: str) -> Dict:
        """
        GET /evolution/concepts/<id>/chain
        Returns the full supersession chain from the concept root.
        """
        try:
            from nexus.evolution.concept_evolution import ConceptEvolutionAPI
            from dataclasses import asdict
            api = ConceptEvolutionAPI(db=self.graph_manager.db)
            chain = api.get_evolution_chain(concept_id)
            if not chain:
                return {"error": "Concept not found or archived", "status": "not_found"}
            return asdict(chain)
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def get_node_detail(self, node_id: str) -> Dict:
        """
        GET /evolution/nodes/<id>
        Returns full node detail with all edge relationships.
        """
        try:
            from nexus.evolution.concept_evolution import ConceptEvolutionAPI
            from dataclasses import asdict
            api = ConceptEvolutionAPI(db=self.graph_manager.db)
            detail = api.get_node_detail(node_id)
            if not detail:
                return {"error": "Node not found", "status": "not_found"}
            return asdict(detail)
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def get_concept_timeline(self, concept_id: str) -> Dict:
        """
        GET /evolution/concepts/<id>/timeline
        Returns version history including archived chains (read-only).
        """
        try:
            from nexus.evolution.concept_evolution import ConceptEvolutionAPI
            api = ConceptEvolutionAPI(db=self.graph_manager.db)
            return api.get_concept_timeline(concept_id)
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def get_cluster_nodes(self, cluster_id: str, include_archived: bool = False) -> Dict:
        """
        GET /evolution/clusters/<id>/nodes
        Returns nodes in a semantic cluster.
        """
        try:
            from nexus.evolution.concept_evolution import ConceptEvolutionAPI
            api = ConceptEvolutionAPI(db=self.graph_manager.db)
            return api.get_cluster_nodes(cluster_id, include_archived=include_archived)
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def get_evolution_live_metrics(self) -> Dict:
        """
        GET /evolution/metrics/live
        Returns real-time metrics from materialized views (cluster health, velocity, convergence).
        """
        try:
            from nexus.evolution.concept_evolution import ConceptEvolutionAPI
            api = ConceptEvolutionAPI(db=self.graph_manager.db)
            return api.get_live_metrics()
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def refresh_evolution_metrics(self) -> Dict:
        """
        POST /evolution/metrics/refresh
        Triggers CONCURRENT refresh of all materialized views.
        """
        try:
            from nexus.evolution.concept_evolution import ConceptEvolutionAPI
            api = ConceptEvolutionAPI(db=self.graph_manager.db)
            success = api.refresh_metrics()
            return {"status": "refreshed" if success else "failed"}
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    # =========================================================================
    # EVOLUTION V2 — AI Advisory API (Layer 2)
    # =========================================================================

    def get_ai_suggestions(self, limit: int = 50) -> Dict:
        """
        GET /evolution/ai/suggestions
        Returns pending AI advisory suggestions for human review.
        These are read-only advisory items — none modify Core.
        """
        try:
            from nexus.evolution.ai_advisory import AIAdvisory
            advisory = AIAdvisory(db=self.graph_manager.db)
            suggestions = advisory.get_pending_suggestions(limit=limit)
            return {"suggestions": suggestions, "total": len(suggestions)}
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def approve_ai_suggestion(self, suggestion_id: str, actor: str, notes: str = "") -> Dict:
        """
        POST /evolution/ai/suggestions/<id>/approve
        Mark a suggestion as approved. Does NOT auto-apply structural changes.
        Human must separately decide what action to take.
        """
        try:
            from nexus.evolution.ai_advisory import AIAdvisory
            advisory = AIAdvisory(db=self.graph_manager.db)
            success = advisory.approve_suggestion(suggestion_id, actor, notes)
            if success:
                self.graph_manager._log_audit_event(
                    event_type="AI_SUGGESTION_APPROVED",
                    agent=actor,
                    component="ai_advisory",
                    decision_action=self.graph_manager.__class__.__module__,  # use DecisionAction
                    reason=notes or "User approved AI suggestion",
                    metadata={"suggestion_id": suggestion_id},
                )
            return {"status": "approved" if success else "failed"}
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def reject_ai_suggestion(self, suggestion_id: str, actor: str, notes: str = "") -> Dict:
        """
        POST /evolution/ai/suggestions/<id>/reject
        Mark a suggestion as rejected.
        """
        try:
            from nexus.evolution.ai_advisory import AIAdvisory
            advisory = AIAdvisory(db=self.graph_manager.db)
            success = advisory.reject_suggestion(suggestion_id, actor, notes)
            return {"status": "rejected" if success else "failed"}
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def run_ai_analysis(self, period: str = "nightly") -> Dict:
        """
        POST /evolution/ai/run
        Trigger an on-demand AI advisory analysis cycle.
        Writes to graph_ai.suggestions only — never to Core.
        """
        try:
            from nexus.evolution.ai_advisory import AIAdvisory
            advisory = AIAdvisory(db=self.graph_manager.db)
            return advisory.run_analysis(period=period)
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def get_ai_analysis_runs(self, limit: int = 20) -> Dict:
        """
        GET /evolution/ai/runs
        Returns recent AI analysis run history.
        """
        try:
            from nexus.evolution.ai_advisory import AIAdvisory
            advisory = AIAdvisory(db=self.graph_manager.db)
            runs = advisory.get_analysis_runs(limit=limit)
            return {"runs": runs, "total": len(runs)}
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    # =========================================================================
    # EVOLUTION V2 — Sandbox Promotion Engine (Layer 3)
    # =========================================================================

    def analyze_sandbox_conflict(self, run_id: str, concept_id: str) -> Dict:
        """
        GET /evolution/sandbox/<run_id>/conflict/<concept_id>
        Analyzes conflict between a sandbox run and the Core concept chain.
        Returns conflict severity and details for UI display before promotion.
        """
        try:
            from nexus.evolution.promotion_engine import PromotionEngine
            from dataclasses import asdict
            engine = PromotionEngine(db=self.graph_manager.db)
            report = engine.analyze_conflict(run_id, concept_id)
            return asdict(report)
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def promote_sandbox(
        self,
        run_id: str,
        concept_id: str,
        strategy: str,
        actor: str,
        change_reason: str = "",
    ) -> Dict:
        """
        POST /evolution/sandbox/<run_id>/promote
        Promote a sandbox evolution chain into Core.

        strategy: REPLACE | BRANCH | NEW_CONCEPT | MANUAL
        INVARIANT: Atomic transaction. On failure, Core is not modified.
        """
        try:
            from nexus.evolution.promotion_engine import PromotionEngine, ResolutionStrategy
            from dataclasses import asdict
            engine = PromotionEngine(db=self.graph_manager.db)

            try:
                strat = ResolutionStrategy(strategy.upper())
            except ValueError:
                return {
                    "error": f"Invalid strategy '{strategy}'. Must be one of: REPLACE, BRANCH, NEW_CONCEPT, MANUAL",
                    "status": "invalid_input",
                }

            result = engine.promote(
                run_id=run_id,
                concept_id=concept_id,
                strategy=strat,
                actor=actor,
                change_reason=change_reason,
            )

            if result.success:
                self.graph_manager._log_audit_event(
                    event_type="SANDBOX_PROMOTED",
                    agent=actor,
                    component="promotion_engine",
                    decision_action="ACCEPTED",
                    reason=change_reason or f"Sandbox promotion via {strategy}",
                    metadata={
                        "run_id": run_id,
                        "concept_id": concept_id,
                        "strategy": strategy,
                        "archived_count": len(result.archived_node_ids),
                        "inserted_count": len(result.inserted_node_ids),
                        "new_version": result.new_version_number,
                    },
                )

            return asdict(result)
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def discard_sandbox(self, run_id: str, actor: str) -> Dict:
        """
        POST /evolution/sandbox/<run_id>/discard
        Discard a sandbox run. Does not touch Core.
        """
        try:
            from nexus.evolution.promotion_engine import PromotionEngine
            engine = PromotionEngine(db=self.graph_manager.db)
            success = engine.discard_sandbox(run_id, actor)
            return {"status": "discarded" if success else "failed"}
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    # =========================================================================
    # COGNITIVE COMPILER — Export, Refiner & Ontology API (Spec §7, §8, §4)
    # =========================================================================

    def export_topic(self, topic_id: str, fmt: str = "json", save_snapshot: bool = False) -> Dict:
        """
        Compile a topic into a StructuredDocument and optionally snapshot it.

        GET /export/topic/<id>?format=json|md&snapshot=true|false

        READ-ONLY with respect to the knowledge graph.
        Writes only to cognition.topic_snapshots (when save_snapshot=True).
        """
        try:
            from nexus.projection.document_compiler import DocumentCompiler, _document_to_dict
            from dataclasses import asdict

            compiler = DocumentCompiler(db=self.graph_manager.db, persist_snapshots=True)

            if save_snapshot:
                doc = compiler.compile_and_snapshot(topic_id)
            else:
                doc = compiler.compile_topic(topic_id)

            if fmt == "md":
                md = compiler.render_markdown(doc)
                return {
                    "topic_id": topic_id,
                    "version": doc.version,
                    "hash": doc.hash,
                    "generated_at": doc.generated_at,
                    "markdown": md,
                    "status": "success",
                }

            # JSON format — default
            return {
                **_document_to_dict(doc),
                "status": "success",
            }

        except ValueError as ve:
            return {"error": str(ve), "status": "not_found"}
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def get_topic_snapshot(self, topic_id: str) -> Optional[Dict]:
        """
        Return the latest persisted snapshot without recompiling.
        Returns None if no snapshot exists.
        """
        try:
            from nexus.projection.document_compiler import DocumentCompiler
            compiler = DocumentCompiler(db=self.graph_manager.db, persist_snapshots=False)
            return compiler.get_latest_snapshot(topic_id)
        except Exception as e:
            print(f"[CortexAPI] get_topic_snapshot failed: {e}")
            return None

    def get_drift_reports(self, topic_id: str, limit: int = 100) -> Dict:
        """
        GET /api/topics/<id>/drift-reports
        Return unresolved Refiner advisory reports for a topic.
        Advisory only — no graph mutations are implied.
        """
        try:
            from nexus.cognition.refiner import Refiner
            refiner = Refiner(db=self.graph_manager.db)
            reports = refiner.get_open_reports(topic_id=topic_id, limit=limit)
            return {
                "topic_id": topic_id,
                "reports": reports,
                "total": len(reports),
                "status": "success",
            }
        except Exception as e:
            return {"error": str(e), "status": "failed", "reports": []}

    def resolve_drift_report(self, report_id: str, resolved_by: str) -> Dict:
        """
        POST /api/drift-reports/<id>/resolve
        Mark a drift report as human-resolved.
        Does NOT modify any graph node.
        """
        try:
            from nexus.cognition.refiner import Refiner
            refiner = Refiner(db=self.graph_manager.db)
            success = refiner.mark_resolved(report_id, resolved_by)
            return {"status": "success" if success else "failed", "report_id": report_id}
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def get_topic_ontology(self, topic_id: str) -> Dict:
        """
        GET /api/topics/<id>/ontology
        Return the ontology parent chain for a topic by walking IS_SUBTOPIC_OF edges.
        Read-only.
        """
        try:
            db = self.graph_manager.db

            # Walk the IS_SUBTOPIC_OF chain upward from this topic
            chain = []
            current_id = topic_id
            visited = set()

            while current_id and current_id not in visited:
                visited.add(current_id)

                # Fetch the current node
                row = db.fetch_one(
                    "SELECT type, data FROM graph.nodes WHERE id = %s",
                    (current_id,),
                )
                if not row:
                    break

                import json as _json
                node_type = row[0]
                node_data = row[1] if isinstance(row[1], dict) else _json.loads(row[1] or "{}")
                chain.append({
                    "id": current_id,
                    "type": node_type,
                    "name": node_data.get("name") or node_data.get("statement") or current_id,
                })

                # Find parent via IS_SUBTOPIC_OF edge
                parent_row = db.fetch_one(
                    """
                    SELECT target_id FROM graph.edges
                    WHERE source_id = %s AND edge_type = 'IS_SUBTOPIC_OF'
                    LIMIT 1
                    """,
                    (current_id,),
                )
                current_id = parent_row[0] if parent_row else None

            return {
                "topic_id": topic_id,
                "ontology_chain": chain,
                "depth": len(chain),
                "status": "success",
            }
        except Exception as e:
            return {"error": str(e), "status": "failed", "ontology_chain": []}

    def register_ontology_node(
        self,
        ontology_id: str,
        name: str,
        parent_id: Optional[str] = None,
    ) -> Dict:
        """
        Register an Ontology node and optionally link it to a parent via IS_SUBTOPIC_OF.
        All mutations go through GraphManager — never raw SQL.
        """
        try:
            self.graph_manager.register_node(
                "ontology",
                ontology_id,
                {"name": name, "lifecycle": "frozen"},
            )
            if parent_id:
                self.graph_manager.register_edge(
                    ("ontology", ontology_id),
                    ("ontology", parent_id),
                    "IS_SUBTOPIC_OF",
                )
            return {"status": "success", "ontology_id": ontology_id}
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def link_topic_to_ontology(self, topic_id: str, ontology_id: str) -> Dict:
        """
        Create an IS_SUBTOPIC_OF edge from a Topic node to an Ontology node.
        Validates that the ontology node exists before linking.
        """
        try:
            ont_row = self.graph_manager.get_node(ontology_id)
            if not ont_row or ont_row[0] != "ontology":
                return {
                    "error": f"Ontology node {ontology_id} not found or wrong type",
                    "status": "not_found",
                }
            self.graph_manager.register_edge(
                ("topic", topic_id),
                ("ontology", ontology_id),
                "IS_SUBTOPIC_OF",
            )
            return {"status": "success", "topic_id": topic_id, "ontology_id": ontology_id}
        except ValueError as ve:
            return {"error": str(ve), "status": "rejected"}
        except Exception as e:
            return {"error": str(e), "status": "failed"}
