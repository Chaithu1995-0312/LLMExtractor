import json
import logging
import time
from typing import Dict, Any, List, Optional
from nexus.cognition.persistence import CognitionLogger
from nexus.db import get_adapter
from nexus.cognition.escalation_router import EscalationRouter
from nexus.cognition.confidence_engine import ConfidenceEngine

logger = logging.getLogger(__name__)

class L3Sage:
    """
    Level 3 (L3) - The Sage
    Role: Strategic Reflection & System Audit.
    Features:
    - Hybrid Escalation (Flash -> Pro)
    - Composite Confidence Scoring (Audit Focused)
    - Budget Awareness
    """

    def __init__(self):
        self.router = EscalationRouter()
        self.confidence_engine = ConfidenceEngine()
        self.logger = CognitionLogger()
        self.db = get_adapter()

    def audit_topic_health(self, topic_id: str) -> Dict[str, Any]:
        """
        Performs a deep strategic audit of a topic's evolution.
        Uses Hybrid Escalation Logic.
        """
        start_time = time.time()
        
        # 1. Gather Metrics (Context)
        metrics = self._fetch_topic_metrics(topic_id)
        snapshot_hash = self.logger.generate_snapshot_hash(metrics)
        metrics_summary_text = json.dumps(metrics, indent=2) # Proxy for text embedding
        
        # 2. Prompts
        system_prompt = (
            "You are the Nexus Sage (Level 3). You are the strategic auditor of the system.\n"
            "Your goal is to detect structural fragility, drift patterns, and ontological conflicts.\n"
            "Analyze the provided topic metrics. Look beyond individual nodes.\n"
            "Identify:\n"
            "1. Clusters with high churn (instability)\n"
            "2. Supersession chains that are oscillating (logical loops)\n"
            "3. Governance recommendations\n"
            "Output strictly JSON: {\"analysis\": \"...\", \"risk_score\": 0.0-1.0, \"recommendations\": [], \"confidence\": 0.0-1.0}"
        )
        
        # 2b. Advisory Memory Injection (pre-prompt hook).
        # Memory context is injected ONLY if retrieval confidence is HIGH.
        # Graph remains canonical — memory is advisory and non-authoritative.
        memory_context_block = self._get_advisory_memory_context(topic_id)

        user_prompt = f"""
        Topic ID: {topic_id}
        Metric Snapshot:
        {metrics_summary_text}
        {memory_context_block}
        Perform strategic audit.
        """
        
        # 3. Execution (Hybrid Flow)
        
        # Attempt 1: Route L3 (Starts at Flash)
        attempt1 = self.router.route_l3(system_prompt, user_prompt)
        result1 = self._parse_response(attempt1["response"])
        
        # Compute Confidence 1
        conf1_data = self.confidence_engine.compute_l3_confidence(
            model_confidence=result1["confidence"],
            analysis=result1["analysis"],
            metrics_summary=metrics_summary_text
        )
        
        final_result = result1
        final_conf_data = conf1_data
        final_tier = attempt1["tier"]
        escalated = False
        
        # Check Threshold
        threshold = attempt1["threshold_target"]
        if conf1_data["final_confidence"] < threshold:
            # ESCALATION TRIGGERED
            print(f"[L3Sage] Low confidence ({conf1_data['final_confidence']} < {threshold}). Escalating to Tier 3 (Pro)...")
            
            attempt2 = self.router.escalate_l3(system_prompt, user_prompt)
            result2 = self._parse_response(attempt2["response"])
            
            conf2_data = self.confidence_engine.compute_l3_confidence(
                model_confidence=result2["confidence"],
                analysis=result2["analysis"],
                metrics_summary=metrics_summary_text
            )
            
            # Log Attempt 1
            self._log_attempt(attempt1, result1, conf1_data, snapshot_hash, user_prompt, start_time, accepted=False)
            
            # Adopt Attempt 2
            final_result = result2
            final_conf_data = conf2_data
            final_tier = attempt2["tier"]
            escalated = True
            
        # 4. Final Logging
        self._log_attempt(
            {"tier": final_tier, "model": "Tier" + str(final_tier)}, 
            final_result, 
            final_conf_data, 
            snapshot_hash, 
            user_prompt, 
            start_time, 
            accepted=True
        )
            
        return final_result

    def _fetch_topic_metrics(self, topic_id: str) -> Dict[str, Any]:
        """
        Aggregates metrics scoped strictly to the topic.
        """
        # A. Basic Counts
        row = self.db.fetch_one(
            """
            SELECT 
                COUNT(*),
                COUNT(*) FILTER (WHERE data->>'lifecycle' = 'active'),
                COUNT(*) FILTER (WHERE data->>'lifecycle' = 'superseded')
            FROM graph.nodes
            WHERE data->>'sync_topic_id' = %s
            """,
            (topic_id,)
        )
        total, active, superseded = row if row else (0,0,0)
        
        # B. Topic-Scoped Churn
        # Join edges to nodes to filter by topic
        churn_row = self.db.fetch_one(
            """
            SELECT COUNT(e.*) 
            FROM graph.edges e
            JOIN graph.nodes n ON e.source_id = n.id
            WHERE e.edge_type = 'SUPERSEDES' 
              AND n.data->>'sync_topic_id' = %s
              AND e.created_at > NOW() - INTERVAL '7 days'
            """,
            (topic_id,)
        )
        
        return {
            "total_nodes": total,
            "active_nodes": active,
            "superseded_nodes": superseded,
            "supersession_ratio": superseded / max(total, 1),
            "topic_churn_7d": churn_row[0] if churn_row else 0
        }

    def _get_advisory_memory_context(self, topic_id: str) -> str:
        """
        Pre-prompt hook: Fetches advisory context from the Memory Layer.

        Retrieves memory chunks related to the topic_id query, evaluates
        retrieval confidence via ConfidenceEngine, and returns a formatted
        context block ONLY if confidence is HIGH enough to be trustworthy.

        Invariants:
          - Memory is advisory ONLY — it augments, never overrides graph data.
          - Returns empty string on low confidence or any failure (silent fallback).
          - MUST NOT raise — this hook must never crash the audit flow.
          - Injection is labeled [ADVISORY MEMORY — NON-AUTHORITATIVE] so the
            LLM understands the epistemic weight of the provided context.
          - Uses ConfidenceEngine for gating — does NOT define its own threshold.

        Returns:
            Formatted string block to append to user_prompt, or "" if skipped.
        """
        # Advisory memory injection threshold — must exceed this to inject.
        # We use a higher bar than summarize() (0.40) since this is LLM input.
        ADVISORY_CONFIDENCE_THRESHOLD = 0.55

        try:
            # Lazy import to avoid circular dependency at module load time.
            from nexus.memory.memory_service import MemoryService
            from nexus.memory.retriever import MemoryRetriever

            # Use retriever directly (no LLM call) to check retrieval quality.
            retriever = MemoryRetriever()
            retrieval_result = retriever.retrieve(
                query=topic_id,
                top_k=5,
            )

            if not retrieval_result.chunks:
                logger.info(
                    "[L3Sage] Advisory memory: no chunks found for topic_id='%s'. Skipping injection.",
                    topic_id,
                )
                self._log_advisory_event(topic_id, "L3_MEMORY_ADVISORY_SKIPPED", reason="no_chunks")
                return ""

            # Evaluate retrieval confidence via ConfidenceEngine.
            all_scores = [c.score for c in retrieval_result.chunks]
            retrieved_texts = [c.text for c in retrieval_result.chunks]
            top_score = retrieval_result.retrieval_metadata.get("top_score", 0.0)

            retrieval_conf = self.confidence_engine.compute_retrieval_confidence(
                top_score=top_score,
                all_scores=all_scores,
                retrieved_texts=retrieved_texts,
                query_text=topic_id,
                threshold=ADVISORY_CONFIDENCE_THRESHOLD,
            )

            if not retrieval_conf["gate_pass"]:
                logger.info(
                    "[L3Sage] Advisory memory: retrieval confidence %.4f below advisory "
                    "threshold %.2f for topic='%s'. Skipping injection.",
                    retrieval_conf["retrieval_confidence"],
                    ADVISORY_CONFIDENCE_THRESHOLD,
                    topic_id,
                )
                self._log_advisory_event(
                    topic_id,
                    "L3_MEMORY_ADVISORY_SKIPPED",
                    reason="low_confidence",
                    confidence=retrieval_conf["retrieval_confidence"],
                )
                return ""

            # Build the advisory context block.
            context_lines = []
            for idx, chunk in enumerate(retrieval_result.chunks, start=1):
                role = chunk.metadata.get("role", "?")
                score = chunk.score
                # Truncate each chunk to avoid prompt bloat.
                text_preview = chunk.text[:400].replace("\n", " ").strip()
                context_lines.append(
                    f"  [{idx}] (score={score:.3f}, role={role}): {text_preview}"
                )

            context_block = "\n".join(context_lines)

            logger.info(
                "[L3Sage] Advisory memory injected: %d chunks, confidence=%.4f for topic='%s'.",
                len(retrieval_result.chunks),
                retrieval_conf["retrieval_confidence"],
                topic_id,
            )
            self._log_advisory_event(
                topic_id,
                "L3_MEMORY_ADVISORY_INJECTED",
                reason="confidence_sufficient",
                confidence=retrieval_conf["retrieval_confidence"],
                chunks_injected=len(retrieval_result.chunks),
            )

            return (
                f"\n[ADVISORY MEMORY — NON-AUTHORITATIVE]\n"
                f"The following context is retrieved from historical memory. "
                f"It is advisory only. Graph data above takes precedence.\n"
                f"Retrieval confidence: {retrieval_conf['retrieval_confidence']:.3f}\n"
                f"{context_block}\n"
                f"[END ADVISORY MEMORY]\n"
            )

        except Exception as exc:
            # Never crash audit_topic_health due to advisory failure.
            logger.warning(
                "[L3Sage] Advisory memory hook failed silently: %s. Proceeding without injection.",
                exc,
            )
            return ""

    def _log_advisory_event(
        self,
        topic_id: str,
        event: str,
        reason: str = "",
        confidence: float = 0.0,
        chunks_injected: int = 0,
    ) -> None:
        """
        Log advisory memory injection events to the cognition logger.

        Uses trigger_event field so events are traceable in cognition_logs.
        """
        try:
            self.logger.log_insight(
                layer="L3",
                topic_id=topic_id,
                trigger_event=event,
                input_snapshot_hash="",
                prompt="",
                output=json.dumps({
                    "reason": reason,
                    "retrieval_confidence": confidence,
                    "chunks_injected": chunks_injected,
                }),
                model="memory_retriever",
                confidence_score=confidence,
                latency_ms=0,
                token_usage=0,
            )
        except Exception as log_exc:
            logger.debug("[L3Sage] Advisory event log failed: %s", log_exc)

    def _parse_response(self, raw_response: str) -> Dict[str, Any]:
        # Handle cases where LLM output is not valid JSON
        # If response is a dict (like from mock/stub), use it directly
        if isinstance(raw_response, dict):
            # Check if it's a STUB response which doesn't follow standard schema
            if raw_response.get("genai_review_status"):
                 return {
                    "analysis": f"API STUB: {raw_response.get('model')} - {raw_response.get('genai_review_status')}",
                    "risk_score": 0.0,
                    "confidence": 0.0 # Force low confidence on stub
                 }
                 
            return {
                "analysis": raw_response.get("analysis", str(raw_response)),
                "risk_score": raw_response.get("risk_score", 0.0),
                "confidence": raw_response.get("confidence", 0.8)
            }
        
        # Default fallback for string response
        default = {"analysis": raw_response, "risk_score": 0.0, "confidence": 0.8}
        
        # Check if it looks like a JSON string of a Stub response (nested stringification)
        if "STUB_OPENAI" in raw_response:
             return {
                "analysis": f"API STUB RESPONSE: {raw_response}",
                "risk_score": 0.0,
                "confidence": 0.0
             }

        try:
            # Handle standard JSON string
            if "{" in raw_response:
                json_str = raw_response[raw_response.find("{"):raw_response.rfind("}")+1]
                parsed = json.loads(json_str)
                # Ensure confidence key exists
                if "confidence" not in parsed:
                    parsed["confidence"] = 0.8
                if "analysis" not in parsed:
                     parsed["analysis"] = str(parsed)
                return parsed
        except:
            pass
        return default

    def _log_attempt(self, attempt_meta, result, conf_data, snap_hash, prompt, start_time, accepted: bool):
        latency = int((time.time() - start_time) * 1000)
        
        # 1. Update usage tracking
        tokens = len(str(result)) // 4
        self.router.budget.track_usage(tokens)

        # 2. Persist V2 Log
        self.logger.log_insight(
            layer="L3",
            topic_id="audit",
            trigger_event="TOPIC_AUDIT_APPROVED" if accepted else "TOPIC_AUDIT_REJECTED",
            input_snapshot_hash=snap_hash,
            prompt="Metrics Snapshot...",
            output=json.dumps(result),
            model=attempt_meta.get("model", "unknown"),
            confidence_score=conf_data["final_confidence"],
            latency_ms=latency,
            token_usage=tokens,
            confidence_components=conf_data["components"],
            threshold_used=attempt_meta.get("threshold_target"),
            escalation_tier=attempt_meta.get("tier"),
            budget_pressure=self.router.budget.get_budget_pressure()
        )
