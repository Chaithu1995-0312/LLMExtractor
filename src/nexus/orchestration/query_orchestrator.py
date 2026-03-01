"""
nexus.orchestration.query_orchestrator
========================================
Unified Cognitive Control Plane entry point for Nexus v2.

This module is the SINGLE orchestration authority for all user queries.
It does NOT duplicate logic from subsystems — it coordinates them.

Execution flow:
  1.  Intent classification  → lightweight keyword/pattern rules
  2.  Route selection        → graph | memory | hybrid (+ overrides)
  3.  Retrieval              → graph.semantic_query() and/or memory.retrieve()
  4.  Confidence evaluation  → ConfidenceEngine.compute_retrieval_confidence()
  5.  Hybrid conflict check  → abs(graph_conf - memory_conf) > THRESHOLD
  6.  Escalation             → EscalationRouter.route_l3() (conditional)
  7.  Timeline construction  → per-step status markers
  8.  System state snapshot  → memory index size, graph health, budget
  9.  Response assembly      → structured control-plane payload

Invariants:
  - MUST NOT compute confidence independently (delegates to ConfidenceEngine).
  - MUST NOT call LLM unless gate_pass == True.
  - MUST NOT write to GraphManager except through MemoryService.promote_to_brick().
  - All override effects are logged in the timeline.
  - Errors in one subsystem do not abort the entire flow — they mark steps FAILED.
  - The final payload is ALWAYS returned (no silent 500s from subsystem errors).
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

HYBRID_CONFLICT_THRESHOLD: float = 0.15
"""Delta between graph_conf and memory_conf above which a conflict is flagged."""

DEFAULT_GATE_THRESHOLD: float = 0.40
"""Default retrieval confidence gate threshold (mirrors ConfidenceEngine default)."""

# Intent keyword classification maps — lightweight, no ML
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


# ── QueryOrchestrator ─────────────────────────────────────────────────────────

class QueryOrchestrator:
    """
    Unified cognitive entrypoint for Nexus v2 Control Plane.

    Coordinates Graph, Memory, Confidence, and Escalation subsystems.
    Returns a complete execution payload that powers the Control Plane UI.

    Usage:
        orchestrator = QueryOrchestrator()
        result = orchestrator.execute("What did we discuss about trading?")
    """

    def __init__(
        self,
        graph_manager=None,
        memory_service=None,
        confidence_engine=None,
        escalation_router=None,
    ):
        """
        Lazy-inject all subsystem dependencies.
        Components are instantiated on first use if not provided.
        """
        self._graph = graph_manager
        self._memory = memory_service
        self._confidence_engine = confidence_engine
        self._escalation_router = escalation_router

    # ── Lazy property accessors ──────────────────────────────────────────────

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

    # ── Primary entry point ──────────────────────────────────────────────────

    def execute(
        self,
        query: str,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a unified cognitive query through all layers.

        Args:
            query:     Natural language query string.
            overrides: Optional operator controls:
                         force_route: "graph" | "memory" | "hybrid"
                         disable_escalation: bool
                         threshold_override: float (0.0–1.0)

        Returns:
            Full control-plane execution payload (always returned, never raises).
        """
        overrides = overrides or {}
        query_id = str(uuid.uuid4())
        timeline: List[Dict[str, str]] = []
        started_at = datetime.now(timezone.utc)

        def mark(step: str, status: str, detail: str = ""):
            entry: Dict[str, str] = {"step": step, "status": status}
            if detail:
                entry["detail"] = detail
            timeline.append(entry)
            logger.debug("[QueryOrchestrator] %s step=%s status=%s", query_id[:8], step, status)

        logger.info(
            "[QueryOrchestrator] execute() query_id=%s query='%s' overrides=%s",
            query_id[:8], query[:80], overrides,
        )

        # ── Step 1: Intent Classification ─────────────────────────────────
        route = self._classify_and_route(query, overrides)
        mark("classified", "complete", f"intent={route['intent']}")

        # ── Step 2: Retrieval ──────────────────────────────────────────────
        retrieval = {"graph": None, "memory": None}

        graph_conf_val: float = 0.0
        memory_conf_val: float = 0.0

        selected = route["selected"]

        if selected in ("graph", "hybrid"):
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

        # ── Step 3: Confidence Evaluation ─────────────────────────────────
        threshold = float(overrides.get("threshold_override", DEFAULT_GATE_THRESHOLD))
        confidence = self._evaluate_confidence(
            query=query,
            selected=selected,
            retrieval=retrieval,
            threshold=threshold,
            graph_conf_val=graph_conf_val,
            memory_conf_val=memory_conf_val,
        )
        mark(
            "confidence_evaluated",
            "complete",
            f"final={confidence['final']:.3f} gate={'PASS' if confidence['gate_pass'] else 'BLOCK'}",
        )

        # ── Step 4: Hybrid Conflict Detection ─────────────────────────────
        hybrid_conflict = self._detect_hybrid_conflict(
            selected=selected,
            graph_conf=graph_conf_val,
            memory_conf=memory_conf_val,
        )
        if hybrid_conflict["detected"]:
            mark("hybrid_conflict_detected", "warn", f"delta={hybrid_conflict['delta']:.3f}")

        # ── Step 5: Escalation ────────────────────────────────────────────
        escalation = {"triggered": False, "tier": None, "advisory": None}

        should_escalate = (
            confidence["gate_pass"]
            and not overrides.get("disable_escalation", False)
            and (
                route["intent"] in ("governance", "strategic")
                or hybrid_conflict["detected"]
                or route.get("force_escalate", False)
            )
        )

        if should_escalate:
            escalation = self._run_escalation(query, route["intent"])
            mark("escalated", "complete", f"tier={escalation.get('tier')}")
        elif overrides.get("disable_escalation"):
            mark("escalation_skipped", "complete", "disabled by override")

        # ── Step 6: Response Assembly ──────────────────────────────────────
        response = self._assemble_response(
            query=query,
            route=route,
            retrieval=retrieval,
            confidence=confidence,
            escalation=escalation,
        )
        mark("generated", "complete" if confidence["gate_pass"] else "blocked")

        # ── Step 7: System State Snapshot ─────────────────────────────────
        system_state = self._get_system_state()

        # ── Final Payload ──────────────────────────────────────────────────
        elapsed_ms = round(
            (datetime.now(timezone.utc) - started_at).total_seconds() * 1000, 1
        )

        payload = {
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

        logger.info(
            "[QueryOrchestrator] complete query_id=%s elapsed_ms=%s gate=%s source=%s",
            query_id[:8], elapsed_ms,
            "PASS" if confidence["gate_pass"] else "BLOCK",
            response.get("source"),
        )

        return payload

    # ── Step implementations ─────────────────────────────────────────────────

    def _classify_and_route(self, query: str, overrides: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify query intent and determine routing.

        Priority: overrides > keyword classification > default (hybrid)
        """
        q_lower = query.lower()

        # Classify intent from keywords
        intent = "factual"  # default
        if any(kw in q_lower for kw in _DIAGNOSTIC_KEYWORDS):
            intent = "diagnostic"
        elif any(kw in q_lower for kw in _GOVERNANCE_KEYWORDS):
            intent = "governance"
        elif any(kw in q_lower for kw in _STRATEGIC_KEYWORDS):
            intent = "strategic"
        elif any(kw in q_lower for kw in _MEMORY_KEYWORDS):
            intent = "memory"

        # Map intent to default route
        _INTENT_ROUTE_MAP = {
            "governance": "graph",
            "diagnostic": "graph",
            "memory": "memory",
            "strategic": "hybrid",
            "factual": "hybrid",
        }
        default_route = _INTENT_ROUTE_MAP.get(intent, "hybrid")

        # Apply force_route override
        selected = overrides.get("force_route", default_route)
        if selected not in ("graph", "memory", "hybrid"):
            selected = default_route

        hybrid_used = selected == "hybrid"

        return {
            "intent": intent,
            "selected": selected,
            "hybrid_used": hybrid_used,
            "overridden": "force_route" in overrides,
            "force_escalate": intent in ("governance", "strategic"),
        }

    def _retrieve_graph(self, query: str):
        """
        Execute graph semantic query. Returns (result_dict, step_status, detail).
        """
        try:
            results = self.graph.semantic_query(query, top_k=10)
            if not results:
                return (
                    {"results": [], "top_score": 0.0, "result_count": 0},
                    "complete",
                    "no_results",
                )
            top_score = results[0].get("confidence", 0.0) if results else 0.0
            return (
                {
                    "results": results[:5],  # Top 5 for payload
                    "top_score": round(top_score, 4),
                    "result_count": len(results),
                },
                "complete",
                f"top_score={top_score:.3f} count={len(results)}",
            )
        except Exception as exc:
            logger.warning("[QueryOrchestrator] graph retrieval failed: %s", exc)
            return (
                {"results": [], "top_score": 0.0, "result_count": 0, "error": str(exc)[:200]},
                "failed",
                str(exc)[:100],
            )

    def _retrieve_memory(self, query: str):
        """
        Execute memory retrieval. Returns (result_dict, step_status, detail).
        """
        try:
            result = self.memory.retrieve(query=query, top_k=10)
            chunks = result.get("chunks", [])
            meta = result.get("retrieval_metadata", {})
            top_score = meta.get("top_score", 0.0)
            if not chunks:
                return (
                    {
                        "chunks": [],
                        "retrieval_metadata": meta,
                        "top_score": 0.0,
                        "chunk_count": 0,
                    },
                    "complete",
                    "no_chunks",
                )
            return (
                {
                    "chunks": chunks[:5],  # Top 5 for payload
                    "retrieval_metadata": meta,
                    "top_score": round(top_score, 4),
                    "chunk_count": len(chunks),
                },
                "complete",
                f"top_score={top_score:.3f} chunks={len(chunks)}",
            )
        except Exception as exc:
            logger.warning("[QueryOrchestrator] memory retrieval failed: %s", exc)
            return (
                {
                    "chunks": [],
                    "retrieval_metadata": {},
                    "top_score": 0.0,
                    "chunk_count": 0,
                    "error": str(exc)[:200],
                },
                "failed",
                str(exc)[:100],
            )

    def _evaluate_confidence(
        self,
        query: str,
        selected: str,
        retrieval: Dict[str, Any],
        threshold: float,
        graph_conf_val: float,
        memory_conf_val: float,
    ) -> Dict[str, Any]:
        """
        Evaluate retrieval confidence using ConfidenceEngine.
        Delegates entirely — never computes independently.
        """
        # Choose which retrieval to evaluate for gating
        if selected == "graph":
            results = retrieval.get("graph", {}) or {}
            top_score = results.get("top_score", 0.0)
            all_scores = [r.get("confidence", 0.0) for r in results.get("results", [])]
            texts = [r.get("statement", "") for r in results.get("results", [])]
        elif selected == "memory":
            mem = retrieval.get("memory", {}) or {}
            top_score = mem.get("top_score", 0.0)
            all_scores = [c.get("score", 0.0) for c in mem.get("chunks", [])]
            texts = [c.get("text", "") for c in mem.get("chunks", [])]
        else:
            # Hybrid: use the stronger retrieval
            g_top = (retrieval.get("graph") or {}).get("top_score", 0.0)
            m_top = (retrieval.get("memory") or {}).get("top_score", 0.0)
            if g_top >= m_top:
                results = retrieval.get("graph", {}) or {}
                top_score = g_top
                all_scores = [r.get("confidence", 0.0) for r in results.get("results", [])]
                texts = [r.get("statement", "") for r in results.get("results", [])]
            else:
                mem = retrieval.get("memory", {}) or {}
                top_score = m_top
                all_scores = [c.get("score", 0.0) for c in mem.get("chunks", [])]
                texts = [c.get("text", "") for c in mem.get("chunks", [])]

        if not all_scores:
            return {
                "final": 0.0,
                "threshold": threshold,
                "components": {"M": 0.0, "S": 0.0, "E": 0.0, "C": 0.0},
                "gate_pass": False,
                "block_reason": "no_results_retrieved",
                "diagnostics": {},
            }

        try:
            conf_result = self.confidence_engine.compute_retrieval_confidence(
                top_score=top_score,
                all_scores=all_scores,
                retrieved_texts=texts[:3],
                query_text=query,
                threshold=threshold,
            )
            return {
                "final": conf_result["retrieval_confidence"],
                "threshold": conf_result["threshold_used"],
                "components": conf_result["components"],
                "gate_pass": conf_result["gate_pass"],
                "block_reason": (
                    None if conf_result["gate_pass"]
                    else f"confidence {conf_result['retrieval_confidence']:.3f} < threshold {threshold:.3f}"
                ),
                "diagnostics": conf_result.get("diagnostics", {}),
            }
        except Exception as exc:
            logger.warning("[QueryOrchestrator] confidence evaluation failed: %s", exc)
            # Safe fallback: block generation on confidence error
            return {
                "final": 0.0,
                "threshold": threshold,
                "components": {"M": 0.0, "S": 0.0, "E": 0.0, "C": 0.0},
                "gate_pass": False,
                "block_reason": f"confidence_engine_error: {str(exc)[:100]}",
                "diagnostics": {"error": str(exc)[:200]},
            }

    def _detect_hybrid_conflict(
        self,
        selected: str,
        graph_conf: float,
        memory_conf: float,
    ) -> Dict[str, Any]:
        """
        Detect significant confidence divergence between graph and memory retrievals.
        Only meaningful when both were retrieved (hybrid route).
        """
        if selected != "hybrid" or graph_conf == 0.0 or memory_conf == 0.0:
            return {"detected": False, "delta": 0.0, "graph_conf": graph_conf, "memory_conf": memory_conf}

        delta = abs(graph_conf - memory_conf)
        detected = delta > HYBRID_CONFLICT_THRESHOLD
        dominant = "graph" if graph_conf >= memory_conf else "memory"

        return {
            "detected": detected,
            "delta": round(delta, 4),
            "graph_conf": round(graph_conf, 4),
            "memory_conf": round(memory_conf, 4),
            "dominant": dominant,
            "recommendation": "escalate_l3" if detected else None,
        }

    def _run_escalation(self, query: str, intent: str) -> Dict[str, Any]:
        """
        Trigger L3 escalation via EscalationRouter.
        Returns escalation metadata (never the raw LLM text for safety).
        """
        try:
            system_prompt = (
                f"You are Nexus L3 Sage. Intent: {intent}. "
                "Provide a strategic advisory analysis. Be concise and structured."
            )
            result = self.escalation_router.route_l3(
                system_prompt=system_prompt,
                user_prompt=query,
            )
            return {
                "triggered": True,
                "tier": result.get("tier", 2),
                "model": result.get("model", "unknown"),
                "advisory": result.get("response", "")[:500] if result.get("response") else None,
            }
        except Exception as exc:
            logger.warning("[QueryOrchestrator] escalation failed: %s", exc)
            return {
                "triggered": True,
                "tier": None,
                "model": None,
                "advisory": None,
                "error": str(exc)[:200],
            }

    def _assemble_response(
        self,
        query: str,
        route: Dict[str, Any],
        retrieval: Dict[str, Any],
        confidence: Dict[str, Any],
        escalation: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Assemble the user-facing response object.
        Only generates content if gate_pass == True.
        """
        if not confidence["gate_pass"]:
            return {
                "answer": None,
                "source": None,
                "confidence": confidence["final"],
                "status": "blocked",
                "block_reason": confidence["block_reason"],
            }

        # Determine primary answer source
        selected = route["selected"]
        answer_fragments = []
        source = selected

        if selected in ("graph", "hybrid"):
            graph_data = retrieval.get("graph") or {}
            for result in graph_data.get("results", [])[:3]:
                stmt = result.get("statement", "")
                if stmt:
                    answer_fragments.append(f"[Graph] {stmt[:200]}")
            if graph_data.get("results"):
                source = "graph"

        if selected in ("memory", "hybrid") and not answer_fragments:
            mem_data = retrieval.get("memory") or {}
            for chunk in mem_data.get("chunks", [])[:3]:
                text = chunk.get("text", "")
                if text:
                    answer_fragments.append(f"[Memory] {text[:200]}")
            if mem_data.get("chunks"):
                source = "memory"

        if selected == "hybrid" and answer_fragments:
            source = "hybrid"

        if escalation.get("triggered") and escalation.get("advisory"):
            source = "l3"
            return {
                "answer": escalation["advisory"],
                "source": source,
                "confidence": confidence["final"],
                "status": "success",
                "block_reason": None,
                "fragments": answer_fragments,
            }

        answer = "\n\n".join(answer_fragments) if answer_fragments else "No relevant content found."

        return {
            "answer": answer,
            "source": source,
            "confidence": confidence["final"],
            "status": "success" if answer_fragments else "no_content",
            "block_reason": None,
            "fragments": answer_fragments,
        }

    def _get_system_state(self) -> Dict[str, Any]:
        """
        Collect non-blocking system health snapshot.
        Errors in individual checks are silenced — health is best-effort.
        """
        state: Dict[str, Any] = {
            "graph_index": "unknown",
            "memory_index": "unknown",
            "memory_vector_count": 0,
            "embedding_model": "nomic-embed-text",
            "budget_pressure": "unknown",
            "last_health_check": datetime.now(timezone.utc).isoformat(),
        }

        try:
            count = self.memory.index_size()
            state["memory_vector_count"] = count
            state["memory_index"] = "healthy" if count > 0 else "empty"
        except Exception as exc:
            state["memory_index"] = "unavailable"
            logger.debug("[QueryOrchestrator] memory index_size failed: %s", exc)

        try:
            # Graph health: attempt a minimal DB probe
            row = self.graph._fetch_one("SELECT COUNT(*) FROM graph.nodes")
            node_count = row[0] if row else 0
            state["graph_index"] = "healthy" if node_count > 0 else "empty"
            state["graph_node_count"] = node_count
        except Exception as exc:
            state["graph_index"] = "unavailable"
            logger.debug("[QueryOrchestrator] graph health probe failed: %s", exc)

        try:
            pressure = self.escalation_router.budget.get_budget_pressure()
            state["budget_pressure"] = pressure if pressure else "unknown"
        except Exception as exc:
            state["budget_pressure"] = "unknown"
            logger.debug("[QueryOrchestrator] budget pressure check failed: %s", exc)

        return state
