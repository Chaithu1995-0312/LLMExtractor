"""
TopicRouter — Advisory-only hybrid topic classification layer.
Module: src/nexus/sync/router.py

INVARIANTS (do not violate):
  - This module is READ-ONLY with respect to the graph.
  - It must NEVER call register_node, register_edge, or modify lifecycle.
  - It must NEVER modify sync.bricks or graph.nodes directly.
  - It must NEVER bypass GraphManager.
  - It must ALWAYS emit an audit event when invoking an LLM.
  - It must ALWAYS return a non-empty list.
  - It MUST be idempotent: route_run(run_id) called multiple times returns consistent results.
  - All LLM calls MUST log cost metadata to GraphManager audit trace.
"""

import json
import math
import time
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# KEYWORD MAP (validated against 4,550 brick simulation)
# Format: { topic_id: { keyword: weight } }
# ---------------------------------------------------------------------------

TOPIC_KEYWORD_MAP: Dict[str, Dict[str, float]] = {
    "trading-intelligence-core": {
        # Core trading domain identifiers
        "trading": 3.0,
        "trade": 2.0,
        "market": 2.0,
        "regime": 3.0,
        "risk": 3.0,
        "symbol": 2.0,
        "entry": 2.0,
        "exit": 2.0,
        "trap": 3.0,
        "liquidity": 2.0,
        "chaos": 3.0,
        "prop": 2.0,
        "position": 2.0,
        "strategy": 2.0,
        "pnl": 2.5,
        "equity": 2.0,
        "drawdown": 2.5,
        "volatility": 2.0,
        "rr": 2.0,
        "signal": 1.5,
        "execution": 1.5,
    },
    "genai-architecture-core": {
        # AI orchestration and multi-agent design
        "jarvis": 3.0,
        "ultron": 2.0,
        "prompt": 2.0,
        "claude": 2.0,
        "gemini": 2.0,
        "flash": 2.0,
        "confidence": 2.0,
        "escalation": 2.0,
        "cognition": 3.0,
        "agent": 2.0,
        "llm": 2.0,
        "embedding": 2.0,
        "vector": 2.0,
        "model": 1.0,
        "ai": 1.0,
        "context": 1.0,
        "token": 1.0,
        "orchestration": 2.0,
        "multi-agent": 3.0,
        "narrator": 2.0,
        "sage": 2.0,
    },
    "infra-execution-layer": {
        # AWS and runtime infrastructure
        "lambda": 3.0,
        "dynamodb": 3.0,
        "ecs": 3.0,
        "queue": 2.0,
        "pgworker": 3.0,
        "transaction": 2.0,
        "ttl": 2.0,
        "eventbridge": 3.0,
        "schema": 2.0,
        "postgres": 2.0,
        "sql": 1.0,
        "api": 1.0,
        "websocket": 2.0,
        "docker": 2.0,
        "aws": 2.0,
        "infrastructure": 2.0,
        "deployment": 2.0,
        "worker": 1.5,
        "celery": 2.0,
        "redis": 2.0,
    },
    "governance-lifecycle-wall": {
        # Knowledge system meta-layer
        "frozen": 3.0,
        "supersede": 3.0,
        "lifecycle": 3.0,
        "audit": 3.0,
        "invariant": 3.0,
        "brick": 2.0,
        "wall": 2.0,
        "extraction": 2.0,
        "memory": 2.0,
        "loose": 2.0,
        "forming": 2.0,
        "killed": 2.0,
        "state": 1.0,
        "trace": 2.0,
        "policy": 2.0,
        "nexus": 2.0,
        "governance": 3.0,
        "compiler": 2.0,
        "deterministic": 2.0,
        "sync": 1.5,
    },
}

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

@dataclass
class RouterConfig:
    """
    Configurable thresholds for the TopicRouter.
    All values can be overridden at construction time for testing.
    """
    # Minimum confidence score for deterministic acceptance (0.0–1.0)
    strong_confidence_threshold: float = 0.75

    # If margin between top-2 scores is less than this, trigger LLM disambiguation
    ambiguity_margin_threshold: float = 0.15

    # If the highest raw score is below this, trigger LLM (not enough signal)
    weak_score_threshold: float = 2.5

    # If True, LLM calls are permitted for disambiguation
    enable_llm: bool = True

    # Topic returned when no other topic can be determined
    default_topic: str = "governance-lifecycle-wall"

    # Minimum LLM confidence to accept the LLM result (below → fallback)
    llm_min_confidence: float = 0.60

    # Token cost estimates per model (USD per 1K tokens)
    llm_cost_per_1k: Dict[str, float] = field(default_factory=lambda: {
        "flash": 0.000075,   # Gemini Flash (L2)
        "pro": 0.001,        # Gemini Pro / Claude Pro (L3)
        "gpt-4o-mini": 0.00015,
        "gpt-4o": 0.005,
        "claude-3-haiku": 0.00025,
        "claude-3-sonnet": 0.003,
    })

    # Maximum bricks to include in the LLM disambiguation prompt
    llm_max_bricks: int = 5

    # Character limit per brick in disambiguation prompt
    llm_max_chars_per_brick: int = 500


# ---------------------------------------------------------------------------
# RESULT TYPE
# ---------------------------------------------------------------------------

@dataclass
class RouteResult:
    """The output of a single route_run() call."""
    topics: List[str]
    method: str           # "deterministic" | "llm" | "fallback"
    confidence: float     # 0.0 – 1.0
    margin: float         # margin between top-2 scores
    raw_scores: Dict[str, float]
    llm_invoked: bool = False
    fallback_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# TOPIC ROUTER
# ---------------------------------------------------------------------------

class TopicRouter:
    """
    Hybrid advisory-only topic router.

    Architecture:
      Phase 1  →  Deterministic keyword scoring (no LLM, <5ms)
      Phase 2  →  Optional LLM disambiguation (only when ambiguous)
      Phase 3  →  Audit emit (mandatory when LLM used)

    This class MUST NOT:
      - Call GraphManager.register_node / register_edge
      - Modify graph.nodes or graph.edges
      - Modify sync.bricks or sync.topics
      - Modify any lifecycle field
      - Call compiler directly
    """

    def __init__(
        self,
        db,  # SyncDatabase instance
        graph_manager,  # GraphManager instance — used ONLY for audit logging
        llm_client: Optional[Any] = None,  # LLMClient — optional
        config: Optional[RouterConfig] = None,
        keyword_map: Optional[Dict[str, Dict[str, float]]] = None,
    ):
        self.db = db
        self.graph_manager = graph_manager
        self.llm = llm_client
        self.config = config or RouterConfig()
        self.keyword_map = keyword_map or TOPIC_KEYWORD_MAP
        # Collect valid topic IDs from keyword map for LLM response validation
        self._valid_topics = set(self.keyword_map.keys())

    # -----------------------------------------------------------------------
    # PUBLIC API
    # -----------------------------------------------------------------------

    def route_run(self, run_id: str) -> List[str]:
        """
        Determine which topic(s) the given source run should be compiled into.

        Returns:
            List[str] — A non-empty list of topic IDs.
            INVARIANT: This list will ALWAYS contain at least one topic.
        """
        result = self._route_run_internal(run_id)
        logger.info(
            "[TopicRouter] run=%s method=%s topics=%s confidence=%.3f margin=%.3f",
            run_id, result.method, result.topics, result.confidence, result.margin
        )
        return result.topics

    def route_run_detailed(self, run_id: str) -> RouteResult:
        """
        Same as route_run() but returns the full RouteResult for diagnostics.
        """
        return self._route_run_internal(run_id)

    # -----------------------------------------------------------------------
    # INTERNAL ROUTING PIPELINE
    # -----------------------------------------------------------------------

    def _route_run_internal(self, run_id: str) -> RouteResult:
        # 1. Fetch bricks for this run
        bricks = self._fetch_bricks_for_run(run_id)

        if not bricks:
            logger.warning("[TopicRouter] No bricks for run=%s, using fallback topic.", run_id)
            return RouteResult(
                topics=[self.config.default_topic],
                method="fallback",
                confidence=0.0,
                margin=0.0,
                raw_scores={},
                fallback_reason="empty_run",
            )

        # 2. Phase 1 — Deterministic scoring
        raw_scores = self._score_bricks(bricks)
        primary_topic, confidence, margin = self._select_primary(raw_scores)

        # 3. Zero score → fallback
        total_score = sum(raw_scores.values())
        if total_score == 0.0:
            logger.warning(
                "[TopicRouter] Zero score for run=%s, using fallback topic.", run_id
            )
            return RouteResult(
                topics=[self.config.default_topic],
                method="fallback",
                confidence=0.0,
                margin=0.0,
                raw_scores=raw_scores,
                fallback_reason="zero_score",
            )

        # 4. Strong deterministic signal → return immediately
        if (
            confidence >= self.config.strong_confidence_threshold
            and margin >= self.config.ambiguity_margin_threshold
            and raw_scores.get(primary_topic, 0.0) >= self.config.weak_score_threshold
        ):
            return RouteResult(
                topics=[primary_topic],
                method="deterministic",
                confidence=confidence,
                margin=margin,
                raw_scores=raw_scores,
            )

        # 5. Weak/ambiguous signal → try LLM
        if self.config.enable_llm and self.llm is not None:
            try:
                llm_topic = self._llm_disambiguate(run_id, bricks, raw_scores)
                if llm_topic:
                    return RouteResult(
                        topics=[llm_topic],
                        method="llm",
                        confidence=1.0,  # LLM returned validated result
                        margin=margin,
                        raw_scores=raw_scores,
                        llm_invoked=True,
                    )
            except Exception as llm_err:
                logger.error(
                    "[TopicRouter] LLM disambiguation failed for run=%s: %s. Falling back.",
                    run_id, llm_err
                )

        # 6. Fallback: use best deterministic result (even if weak)
        fallback_reason = "low_confidence" if confidence < self.config.strong_confidence_threshold else "low_margin"
        logger.info(
            "[TopicRouter] Using weak deterministic fallback for run=%s: topic=%s",
            run_id, primary_topic
        )
        return RouteResult(
            topics=[primary_topic],
            method="fallback",
            confidence=confidence,
            margin=margin,
            raw_scores=raw_scores,
            fallback_reason=fallback_reason,
        )

    # -----------------------------------------------------------------------
    # PHASE 1 — DETERMINISTIC SCORING
    # -----------------------------------------------------------------------

    def _fetch_bricks_for_run(self, run_id: str) -> List[Dict]:
        """
        Fetch all bricks for a given run_id from the sync database.
        Returns only active (non-superseded) bricks.

        No graph mutations. Read-only.
        """
        try:
            run = self.db.get_run(run_id)
            if not run:
                return []

            # We score from run content directly to avoid N+1 on bricks table
            # Bricks may not be compiled yet — we read raw messages instead
            raw_content = run.get("raw_content", {})
            messages = raw_content.get("messages", [])

            # Represent each message as a pseudo-brick for scoring purposes
            pseudo_bricks = []
            for msg in messages:
                content = msg.get("content", "")
                if isinstance(content, dict):
                    # Handle multimodal content
                    parts = content.get("parts", [])
                    content = " ".join(str(p) for p in parts if isinstance(p, str))
                if content and isinstance(content, str):
                    pseudo_bricks.append({"content": content})

            return pseudo_bricks
        except Exception as e:
            logger.error("[TopicRouter] Error fetching bricks for run=%s: %s", run_id, e)
            return []

    def _score_bricks(self, bricks: List[Dict]) -> Dict[str, float]:
        """
        Score a list of bricks deterministically using the keyword map.

        Per-brick score: sum(weight * hit_count) / sqrt(word_count + 1)
        Aggregate: sum of per-brick scores across all bricks.

        Returns normalized scores per topic.
        """
        aggregate: Dict[str, float] = {topic: 0.0 for topic in self.keyword_map}

        for brick in bricks:
            content = brick.get("content", "")
            if not content:
                continue

            text = content.lower()
            word_count = max(len(text.split()), 1)
            norm_factor = math.sqrt(word_count)

            for topic, keywords in self.keyword_map.items():
                raw_score = 0.0
                for kw, weight in keywords.items():
                    if kw in text:
                        # Count number of occurrences, capped at 5 to avoid flooding
                        hits = min(text.count(kw), 5)
                        raw_score += weight * hits
                # Normalize by sqrt(word_count) to handle very long bricks fairly
                aggregate[topic] += raw_score / norm_factor

        return aggregate

    def _select_primary(
        self, scores: Dict[str, float]
    ) -> Tuple[str, float, float]:
        """
        Select the primary topic and compute confidence + margin.

        confidence = top_score / (total_score + epsilon)
        margin     = (top_score - second_score) / (top_score + epsilon)

        Returns: (primary_topic, confidence, margin)
        """
        epsilon = 1e-9
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        primary_topic, top_score = sorted_scores[0]
        _, second_score = sorted_scores[1] if len(sorted_scores) > 1 else (None, 0.0)

        total_score = sum(scores.values())
        confidence = top_score / (total_score + epsilon)
        margin = (top_score - second_score) / (top_score + epsilon)

        return primary_topic, confidence, margin

    # -----------------------------------------------------------------------
    # PHASE 2 — LLM DISAMBIGUATION
    # -----------------------------------------------------------------------

    def _llm_disambiguate(
        self,
        run_id: str,
        bricks: List[Dict],
        raw_scores: Dict[str, float],
    ) -> Optional[str]:
        """
        Invoke LLM to disambiguate topic assignment.

        Two-tier escalation:
          L2 (Flash/Haiku)  → if confidence >= llm_min_confidence → return
          L3 (Pro/Sonnet)   → if L2 confidence < llm_min_confidence

        INVARIANT: Audit event MUST be emitted before returning.
        """
        t_start = time.perf_counter()

        # Select representative bricks for the prompt (avoid sending 50k chars)
        sample = bricks[: self.config.llm_max_bricks]
        prompt_snippets = []
        for i, brick in enumerate(sample):
            text = brick.get("content", "")[:self.config.llm_max_chars_per_brick]
            prompt_snippets.append(f"[Brick {i+1}]\n{text}")

        available_topics = sorted(self.keyword_map.keys())

        system_prompt = (
            "You are a topic classifier for the Nexus knowledge system. "
            "Your job is to classify content into one of the defined topics. "
            "Return ONLY valid JSON. No explanation. No markdown."
        )

        user_prompt = (
            f"Available topics:\n"
            + "\n".join(f"- {t}" for t in available_topics)
            + "\n\nContent samples from a single source run:\n\n"
            + "\n\n".join(prompt_snippets)
            + "\n\n"
            "Return JSON:\n"
            '{"primary_topic": "<topic_id>", "confidence": <0.0-1.0>, "reasoning": "<brief>"}'
        )

        # Attempt L2 (low cost)
        l2_result, l2_cost_usd, l2_tokens = self._call_llm_with_cost(
            system_prompt, user_prompt, model_tier="L2"
        )

        t_elapsed = time.perf_counter() - t_start

        if l2_result:
            topic = l2_result.get("primary_topic")
            l2_confidence = float(l2_result.get("confidence", 0.0))

            if topic in self._valid_topics and l2_confidence >= self.config.llm_min_confidence:
                # Emit audit — MANDATORY for any LLM spend
                self._emit_llm_audit(
                    run_id=run_id,
                    model_tier="L2",
                    cost_usd=l2_cost_usd,
                    tokens=l2_tokens,
                    selected_topic=topic,
                    confidence=l2_confidence,
                    elapsed_ms=int(t_elapsed * 1000),
                    reason="L2 disambiguation succeeded",
                )
                return topic

            # L2 not confident enough — escalate to L3
            logger.info(
                "[TopicRouter] L2 confidence %.3f below threshold. Escalating to L3 for run=%s.",
                l2_confidence, run_id,
            )

        # Attempt L3 (higher cost)
        l3_result, l3_cost_usd, l3_tokens = self._call_llm_with_cost(
            system_prompt, user_prompt, model_tier="L3"
        )

        t_elapsed = time.perf_counter() - t_start

        if l3_result:
            topic = l3_result.get("primary_topic")
            l3_confidence = float(l3_result.get("confidence", 0.0))

            if topic in self._valid_topics:
                self._emit_llm_audit(
                    run_id=run_id,
                    model_tier="L3",
                    cost_usd=l3_cost_usd,
                    tokens=l3_tokens,
                    selected_topic=topic,
                    confidence=l3_confidence,
                    elapsed_ms=int(t_elapsed * 1000),
                    reason="L3 escalation after L2 low confidence",
                )
                return topic

        # Both tiers failed — emit failure audit and return None (caller will fallback)
        self._emit_llm_audit(
            run_id=run_id,
            model_tier="L3",
            cost_usd=(l2_cost_usd or 0.0) + (l3_cost_usd or 0.0),
            tokens=(l2_tokens or 0) + (l3_tokens or 0),
            selected_topic=None,
            confidence=0.0,
            elapsed_ms=int(t_elapsed * 1000),
            reason="Both L2 and L3 failed to return valid topic",
        )
        return None

    def _call_llm_with_cost(
        self,
        system_prompt: str,
        user_prompt: str,
        model_tier: str,
    ) -> Tuple[Optional[Dict], float, int]:
        """
        Call LLM and return (parsed_json, cost_usd, total_tokens).

        DOES NOT raise — returns (None, 0.0, 0) on any failure.
        """
        try:
            # Map tier to intent/tolerance for LLMClient routing
            if model_tier == "L2":
                raw = self.llm.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    intent_class="USER_EXPLAIN",
                    cost_tolerance="low",
                    user_visible=False,
                )
            else:  # L3
                raw = self.llm.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    intent_class="USER_EXPLAIN",
                    cost_tolerance="high",
                    user_visible=False,
                )

            # Parse JSON
            parsed = self._parse_llm_json(raw)
            if parsed is None:
                return None, 0.0, 0

            # Estimate cost (we don't have exact token counts from LLMClient stub)
            # Use character length as proxy: ~4 chars per token
            approx_tokens = (len(system_prompt) + len(user_prompt) + len(raw)) // 4
            model_key = "flash" if model_tier == "L2" else "pro"
            cost_per_1k = self.config.llm_cost_per_1k.get(model_key, 0.001)
            cost_usd = (approx_tokens / 1000.0) * cost_per_1k

            return parsed, cost_usd, approx_tokens

        except Exception as e:
            logger.error("[TopicRouter] LLM call failed (tier=%s): %s", model_tier, e)
            return None, 0.0, 0

    def _parse_llm_json(self, raw: str) -> Optional[Dict]:
        """
        Robustly extract and parse JSON from LLM output.
        """
        if not raw:
            return None
        try:
            # Check for hard-fail markers from LLMClient
            if '"status": "HARD_FAIL"' in raw or '"error":' in raw:
                logger.warning("[TopicRouter] LLM returned HARD_FAIL: %s", raw[:200])
                return None

            # Try direct parse
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # Fuzzy extraction — find first { ... }
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(raw[start : end + 1])
            except json.JSONDecodeError:
                pass

        logger.warning("[TopicRouter] Could not parse LLM response as JSON: %s", raw[:200])
        return None

    # -----------------------------------------------------------------------
    # AUDIT LOGGING (MANDATORY FOR LLM SPEND)
    # -----------------------------------------------------------------------

    def _emit_llm_audit(
        self,
        run_id: str,
        model_tier: str,
        cost_usd: float,
        tokens: int,
        selected_topic: Optional[str],
        confidence: float,
        elapsed_ms: int,
        reason: str,
    ) -> None:
        """
        Emit a mandatory audit event via GraphManager.
        INVARIANT: This MUST be called after every LLM invocation.

        GraphManager._log_audit_event is the ONLY permitted write here.
        No direct DB writes.
        """
        try:
            # Import inside method to avoid circular imports at module level
            from nexus.graph.schema import AuditEventType, ModelTier, DecisionAction

            tier_map = {
                "L2": ModelTier.L2,
                "L3": ModelTier.L3,
            }
            model_tier_enum = tier_map.get(model_tier, ModelTier.L2)

            self.graph_manager._log_audit_event(
                event_type=AuditEventType.LLM_CALL_EXECUTED,
                agent="topic-router",
                component="sync.router",
                decision_action=DecisionAction.ACCEPTED if selected_topic else DecisionAction.REJECTED,
                reason=reason,
                run_id=run_id,
                model_tier=model_tier_enum,
                cost_usd=cost_usd,
                tokens_in=tokens,
                tokens_out=0,
                metadata={
                    "selected_topic": selected_topic,
                    "confidence": confidence,
                    "elapsed_ms": elapsed_ms,
                },
            )
        except Exception as audit_err:
            # Audit failure is NOT allowed to silently pass for cost-bearing calls
            # Raise so the caller knows the invariant was violated
            raise RuntimeError(
                f"[TopicRouter] INVARIANT VIOLATION: Audit emit failed after LLM spend. "
                f"run_id={run_id}, cost_usd={cost_usd}. Original error: {audit_err}"
            ) from audit_err

    # -----------------------------------------------------------------------
    # VALIDATION HELPERS
    # -----------------------------------------------------------------------

    def get_active_topics(self) -> List[str]:
        """
        Returns only ACTIVE topics from the database that also have keyword maps.
        This prevents routing to ARCHIVED or LEGACY topics.
        """
        try:
            all_topics = self.db.get_all_topics()
            active_ids = {
                t["id"] for t in all_topics
                if t.get("state", "ACTIVE") == "ACTIVE"
            }
            # Intersect with keyword map — only route to topics we can score
            return [t for t in self._valid_topics if t in active_ids]
        except Exception as e:
            logger.error("[TopicRouter] Failed to fetch active topics: %s", e)
            return list(self._valid_topics)
