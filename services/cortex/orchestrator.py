from __future__ import annotations

from inspect import isawaitable
from typing import Any, Dict, Optional

from services.cortex.feedback import Feedback
from services.cortex.reasoner import GraphReasoner


class Orchestrator:
    """
    Central async-compatible control layer for ingestion/processing.

    This module is intentionally additive and minimal: it does not alter any
    existing runtime wiring unless explicitly invoked by callers.
    """

    def __init__(
        self,
        extractor,
        validator,
        graph,
        storage,
        llm_client,
        agent=None,
        local_model=None,
    ):
        self.extractor = extractor
        self.validator = validator
        self.graph = graph
        self.storage = storage
        self.llm = llm_client
        self.agent = agent
        self.local_model = local_model
        self.feedback = Feedback()
        self.reasoner = GraphReasoner(self.graph)

    async def process(self, input_data: Dict[str, Any], mode: str = "default") -> Dict[str, Any]:
        # Step 1: decision layer
        decision: Optional[Dict[str, Any]] = None
        if self.agent:
            decision = self.agent.decide(input_data, mode)

        # enforce decision
        if decision:
            if decision.get("store") is False:
                result = {"status": "skipped", "reason": "agent_decision", "decision": decision}
                self._record_feedback(input_data, mode, result)
                return result

            if decision.get("priority") == "low":
                # optional throttle / skip hook
                pass

        # Step 2: LLM gating
        use_llm = True
        if self.local_model:
            confidence = 0.0
            if hasattr(self.local_model, "predict"):
                confidence = float(self.local_model.predict(input_data))
            if confidence > 0.8:
                use_llm = False

        # Step 3: extraction
        if use_llm:
            extracted = self.extractor.run(input_data, mode=mode)
            if isawaitable(extracted):
                extracted = await extracted
        else:
            extracted = self.local_model.extract(input_data)
            if isawaitable(extracted):
                extracted = await extracted

        # Step 4: validation
        valid_data = self.validator.validate(extracted)
        if mode == "trading" and not valid_data:
            result = {"status": "rejected", "reason": "validation_failed", "decision": decision}
            self._record_feedback(input_data, mode, result)
            return result

        if mode != "decision" and not valid_data:
            result = {"status": "rejected", "reason": "validation_failed", "decision": decision}
            self._record_feedback(input_data, mode, result)
            return result

        if mode == "decision" and not valid_data:
            # allow partial continuation in decision mode
            valid_data = extracted

        # Step 5: graph insert
        graph_result = self.graph.insert(valid_data)
        if isawaitable(graph_result):
            graph_result = await graph_result
        nodes, edges = graph_result

        # Step 5.5: reasoning hooks
        patterns = []
        try:
            patterns = self.reasoner.find_patterns("entity")
        except Exception:
            patterns = []

        signal_score = 0.0
        if nodes:
            try:
                signal_score = self.reasoner.score_signal(nodes[0])
            except Exception:
                signal_score = 0.0

        # Step 6: persistence
        save_result = self.storage.save(nodes, edges)
        if isawaitable(save_result):
            await save_result

        result = {
            "status": "success",
            "nodes": nodes,
            "edges": edges,
            "decision": decision,
            "patterns": patterns,
            "signal_score": signal_score,
        }
        self._record_feedback(input_data, mode, result)
        return result

    def _record_feedback(self, input_data: Dict[str, Any], mode: str, outcome: Dict[str, Any]) -> None:
        try:
            self.feedback.record(
                {
                    "input": input_data,
                    "result": outcome.get("status", "unknown"),
                    "mode": mode,
                    "reason": outcome.get("reason"),
                    "decision": outcome.get("decision"),
                }
            )
        except Exception:
            # feedback logging is non-blocking
            pass
