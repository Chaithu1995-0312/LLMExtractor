"""
nexus.orchestration.query_orchestrator
========================================
Unified Cognitive Control Plane entry point for Nexus v2.
"""

import logging
import uuid
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

HYBRID_CONFLICT_THRESHOLD: float = 0.15
DEFAULT_GATE_THRESHOLD: float = 0.40

_GOVERNANCE_KEYWORDS = frozenset({
    "audit", "risk", "cluster", "governance", "policy", "compliance",
    "lifecycle", "frozen", "supersede", "kill", "promote",
})
_DIAGNOSTIC_KEYWORDS = frozenset({
    "why", "blocked", "reason", "explain", "debug", "trace",
    "how was", "what happened", "confidence",
})
_MEMORY_KEYWORDS = frozenset({
    "discussed", "remember", "recall", "history", "conversation",
    "mentioned", "said", "told", "talked about", "previously",
})
_STRATEGIC_KEYWORDS = frozenset({
    "should we", "recommend", "suggest", "strategy", "plan",
    "next step", "advise", "analyze", "synthesize",
})
_INTENT_KEYWORDS = frozenset({
    "project", "intent", "momentum", "status", "active", "loose", "forming",
    "unfinished", "incomplete", "evolution",
})


# ── QueryOrchestrator ─────────────────────────────────────────────────────────

class QueryOrchestrator:
    def __init__(
        self,
        graph_manager=None,
        memory_service=None,
        confidence_engine=None,
        escalation_router=None,
    ):
        self._graph = graph_manager
        self._memory = memory_service
        self._confidence_engine = confidence_engine
        self._escalation_router = escalation_router

    @property
    def graph(self):
        if self._graph is None:
            from nexus.graph.manager import GraphManager
            self._graph = GraphManager()
        return self._graph

    @property
    def memory(self):
        if self._memory is None:
            from nexus.memory.memory_service import MemoryService
            self._memory = MemoryService()
        return self._memory

    @property
    def confidence_engine(self):
        if self._confidence_engine is None:
            from nexus.cognition.confidence_engine import ConfidenceEngine
            self._confidence_engine = ConfidenceEngine()
        return self._confidence_engine

    @property
    def escalation_router(self):
        if self._escalation_router is None:
            from nexus.cognition.escalation_router import EscalationRouter
            self._escalation_router = EscalationRouter()
        return self._escalation_router

    def execute(
        self,
        query: str,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        overrides = overrides or {}
        query_id = str(uuid.uuid4())
        timeline: List[Dict[str, str]] = []
        started_at = datetime.now(timezone.utc)

        def mark(step: str, status: str, detail: str = ""):
            entry: Dict[str, str] = {"step": step, "status": status}
            if detail:
                entry["detail"] = detail
            timeline.append(entry)

        route = self._classify_and_route(query, overrides)
        mark("classified", "complete", f"intent={route['intent']}")

        retrieval = {"graph": None, "memory": None}
        graph_conf_val: float = 0.0
        memory_conf_val: float = 0.0
        selected = route["selected"]

        if selected in ("graph", "hybrid", "intent_reasoning"):
            graph_result, g_step_status, g_detail = self._retrieve_graph(query)
            retrieval["graph"] = graph_result
            mark("graph_retrieved", g_step_status, g_detail)
            if graph_result and graph_result.get("results"):
                graph_conf_val = graph_result.get("top_score", 0.0)

        if selected in ("memory", "hybrid"):
            memory_result, m_step_status, m_detail = self._retrieve_memory(query)
            retrieval["memory"] = memory_result
            mark("memory_retrieved", m_step_status, m_detail)
            if memory_result and memory_result.get("chunks"):
                memory_conf_val = memory_result.get("retrieval_metadata", {}).get("top_score", 0.0)

        threshold = float(overrides.get("threshold_override", DEFAULT_GATE_THRESHOLD))
        confidence = self._evaluate_confidence(
            query=query,
            selected=selected,
            retrieval=retrieval,
            threshold=threshold,
            graph_conf_val=graph_conf_val,
            memory_conf_val=memory_conf_val,
        )
        mark("confidence_evaluated", "complete", f"final={confidence['final']:.3f}")

        hybrid_conflict = self._detect_hybrid_conflict(selected, graph_conf_val, memory_conf_val)
        
        escalation = {"triggered": False, "tier": None, "advisory": None}
        should_escalate = confidence["gate_pass"] and not overrides.get("disable_escalation", False) and (
            route["intent"] in ("governance", "strategic") or hybrid_conflict["detected"]
        )

        if should_escalate:
            escalation = self._run_escalation(query, route["intent"])
            mark("escalated", "complete", f"tier={escalation.get('tier')}")

        response = self._assemble_response(query, route, retrieval, confidence, escalation)
        mark("generated", "complete" if confidence["gate_pass"] else "blocked")

        system_state = self._get_system_state()
        elapsed_ms = round((datetime.now(timezone.utc) - started_at).total_seconds() * 1000, 1)

        return {
            "query_id": query_id,
            "query": query,
            "elapsed_ms": elapsed_ms,
            "route": route,
            "retrieval": retrieval,
            "confidence": confidence,
            "hybrid_conflict": hybrid_conflict,
            "escalation": escalation,
            "timeline": timeline,
            "system_state": system_state,
            "response": response,
        }

    def _classify_and_route(self, query: str, overrides: Dict[str, Any]) -> Dict[str, Any]:
        q_lower = query.lower()
        intent = "factual"
        if any(kw in q_lower for kw in _DIAGNOSTIC_KEYWORDS): intent = "diagnostic"
        elif any(kw in q_lower for kw in _GOVERNANCE_KEYWORDS): intent = "governance"
        elif any(kw in q_lower for kw in _STRATEGIC_KEYWORDS): intent = "strategic"
        elif any(kw in q_lower for kw in _MEMORY_KEYWORDS): intent = "memory"
        elif any(kw in q_lower for kw in _INTENT_KEYWORDS): intent = "intent_reasoning"

        _MAP = {
            "governance": "graph", "diagnostic": "graph", "memory": "memory",
            "strategic": "hybrid", "factual": "hybrid", "intent_reasoning": "graph"
        }
        selected = overrides.get("force_route", _MAP.get(intent, "hybrid"))
        return {"intent": intent, "selected": selected, "hybrid_used": selected == "hybrid"}

    def _retrieve_graph(self, query: str):
        try:
            results = self.graph.semantic_query(query, top_k=10)
            top_score = results[0].get("confidence", 0.0) if results else 0.0
            return ({"results": results[:5], "top_score": round(top_score, 4), "result_count": len(results)}, "complete", f"top={top_score:.3f}")
        except Exception as exc:
            return ({"results": [], "top_score": 0.0, "error": str(exc)}, "failed", str(exc)[:50])

    def _retrieve_memory(self, query: str):
        try:
            result = self.memory.retrieve(query=query, top_k=10)
            chunks = result.get("chunks", [])
            top_score = result.get("retrieval_metadata", {}).get("top_score", 0.0)
            return ({"chunks": chunks[:5], "top_score": round(top_score, 4), "chunk_count": len(chunks)}, "complete", f"top={top_score:.3f}")
        except Exception as exc:
            return ({"chunks": [], "top_score": 0.0, "error": str(exc)}, "failed", str(exc)[:50])

    def _evaluate_confidence(self, query, selected, retrieval, threshold, graph_conf_val, memory_conf_val):
        # Simplified for logic flow, delegates to confidence_engine in real impl
        top_score = max(graph_conf_val, memory_conf_val)
        gate_pass = top_score >= threshold
        return {"final": top_score, "gate_pass": gate_pass, "threshold": threshold, "block_reason": None if gate_pass else "low_confidence"}

    def _detect_hybrid_conflict(self, selected, g_conf, m_conf):
        delta = abs(g_conf - m_conf)
        return {"detected": selected == "hybrid" and delta > HYBRID_CONFLICT_THRESHOLD, "delta": delta}

    def _run_escalation(self, query, intent):
        return {"triggered": True, "tier": 2, "advisory": "L3 analysis placeholder"}

    def _assemble_response(self, query, route, retrieval, confidence, escalation):
        if route["intent"] == "intent_reasoning":
            return self._reason_about_intents(query, retrieval)
        
        if not confidence["gate_pass"]:
            return {"answer": None, "status": "blocked", "block_reason": confidence["block_reason"]}
        
        return {"answer": "Factual answer placeholder", "status": "success"}

    def _reason_about_intents(self, query, retrieval) -> Dict[str, Any]:
        """
        L4 Cognitive Reasoning about Intents.
        """
        # Fetch actual Intent data from DB
        intents = self.graph.get_all_intents()
        
        if "active" in query.lower():
            filtered = [i for i in intents if i.lifecycle.value == "active"]
            msg = f"Found {len(filtered)} active projects."
        elif "forming" in query.lower():
            filtered = [i for i in intents if i.lifecycle.value == "forming"]
            msg = f"Found {len(filtered)} projects currently forming."
        else:
            filtered = intents
            msg = f"Total project count: {len(filtered)}."

        answer = msg + "\n" + "\n".join([f"- {i.name} (Status: {i.lifecycle.value})" for i in filtered[:10]])
        
        return {
            "answer": answer,
            "source": "graph_intent",
            "status": "success"
        }

    def _get_system_state(self):
        return {"status": "healthy"}
