"""
Unit tests for TopicRouter (src/nexus/sync/router.py)
Coverage: 20 test cases per implementation packet specification.

Run with: pytest tests/unit/test_topic_router.py -v
"""
import json
import pytest
from unittest.mock import MagicMock
from nexus.sync.router import TopicRouter, RouterConfig, TOPIC_KEYWORD_MAP

# ---------------------------------------------------------------------------
# FIXTURES
# ---------------------------------------------------------------------------

TRADING_MSGS = {"messages": [
    {"role": "user", "content": "The trading regime risk strategy uses trap entries with chaos scores and drawdown limits."},
    {"role": "assistant", "content": "Risk management for prop trading uses volatility-adjusted position sizing with RR targets."},
]}

INFRA_MSGS = {"messages": [
    {"role": "user", "content": "Lambda function triggers DynamoDB TTL cleanup via EventBridge. The ECS worker handles queue processing."},
    {"role": "assistant", "content": "AWS infrastructure uses Postgres transactions and Docker deployment with Redis caching."},
]}

GOVERNANCE_MSGS = {"messages": [
    {"role": "user", "content": "The brick lifecycle starts as loose, transitions to forming after audit invariant check. Frozen bricks cannot be superseded."},
    {"role": "assistant", "content": "Wall governance requires deterministic compiler trace. Nexus policy: no silent mutation allowed."},
]}

GENAI_MSGS = {"messages": [
    {"role": "user", "content": "Jarvis uses Claude and Gemini flash for multi-agent orchestration. LLM cognition escalation routes to Sage."},
    {"role": "assistant", "content": "The confidence engine routes low-confidence prompts from narrator agent to L3 model tier."},
]}

AMBIGUOUS_MSGS = {"messages": [
    {"role": "user", "content": "risk"},
    {"role": "assistant", "content": "state"},
]}

EMPTY_MSGS = {"messages": []}


def make_db(run_content=None):
    db = MagicMock()
    db.get_run.return_value = {
        "id": "run-001",
        "raw_content": run_content if run_content is not None else {"messages": []},
        "status": "CLOSED",
        "last_processed_index": -1,
    }
    db.get_all_topics.return_value = [
        {"id": "trading-intelligence-core", "state": "ACTIVE"},
        {"id": "genai-architecture-core", "state": "ACTIVE"},
        {"id": "infra-execution-layer", "state": "ACTIVE"},
        {"id": "governance-lifecycle-wall", "state": "ACTIVE"},
    ]
    return db


def make_gm():
    gm = MagicMock()
    gm._log_audit_event = MagicMock()
    return gm


def make_router(db=None, gm=None, llm=None, config=None):
    return TopicRouter(
        db=db or make_db(),
        graph_manager=gm or make_gm(),
        llm_client=llm,
        config=config,
    )


# ---------------------------------------------------------------------------
# TEST 1: Strong deterministic classification — Trading
# ---------------------------------------------------------------------------

def test_strong_deterministic_trading():
    router = make_router(db=make_db(TRADING_MSGS))
    topics = router.route_run("run-001")
    assert len(topics) == 1
    assert topics[0] == "trading-intelligence-core"


# ---------------------------------------------------------------------------
# TEST 2: Strong deterministic classification — Infra
# ---------------------------------------------------------------------------

def test_strong_deterministic_infra():
    router = make_router(db=make_db(INFRA_MSGS))
    topics = router.route_run("run-001")
    assert len(topics) == 1
    assert topics[0] == "infra-execution-layer"


# ---------------------------------------------------------------------------
# TEST 3: Strong deterministic classification — Governance
# ---------------------------------------------------------------------------

def test_strong_deterministic_governance():
    router = make_router(db=make_db(GOVERNANCE_MSGS))
    topics = router.route_run("run-001")
    assert len(topics) == 1
    assert topics[0] == "governance-lifecycle-wall"


# ---------------------------------------------------------------------------
# TEST 4: Strong deterministic classification — GenAI
# ---------------------------------------------------------------------------

def test_strong_deterministic_genai():
    router = make_router(db=make_db(GENAI_MSGS))
    topics = router.route_run("run-001")
    assert len(topics) == 1
    assert topics[0] == "genai-architecture-core"


# ---------------------------------------------------------------------------
# TEST 5: Ambiguity triggers LLM and succeeds
# ---------------------------------------------------------------------------

def test_ambiguity_triggers_llm():
    gm = make_gm()
    llm = MagicMock()
    llm.generate.return_value = json.dumps({
        "primary_topic": "trading-intelligence-core",
        "confidence": 0.82,
        "reasoning": "Risk signals dominate."
    })
    config = RouterConfig(strong_confidence_threshold=0.99, enable_llm=True)
    router = make_router(db=make_db(AMBIGUOUS_MSGS), gm=gm, llm=llm, config=config)

    topics = router.route_run("run-001")

    assert len(topics) == 1
    assert topics[0] == "trading-intelligence-core"
    # Audit MUST be emitted after LLM call
    gm._log_audit_event.assert_called_once()


# ---------------------------------------------------------------------------
# TEST 6: LLM L2 low confidence escalates to L3
# ---------------------------------------------------------------------------

def test_llm_escalation_l2_to_l3():
    gm = make_gm()
    call_count = [0]

    def mock_generate(**kwargs):
        call_count[0] += 1
        if kwargs.get("cost_tolerance") == "low":
            return json.dumps({"primary_topic": "trading-intelligence-core", "confidence": 0.40, "reasoning": "Weak."})
        return json.dumps({"primary_topic": "governance-lifecycle-wall", "confidence": 0.91, "reasoning": "L3 clear."})

    llm = MagicMock()
    llm.generate.side_effect = lambda **kwargs: mock_generate(**kwargs)

    config = RouterConfig(strong_confidence_threshold=0.99, llm_min_confidence=0.60, enable_llm=True)
    router = make_router(db=make_db(AMBIGUOUS_MSGS), gm=gm, llm=llm, config=config)
    topics = router.route_run("run-001")

    assert topics[0] == "governance-lifecycle-wall"
    assert call_count[0] == 2  # L2 + L3 both called
    gm._log_audit_event.assert_called_once()


# ---------------------------------------------------------------------------
# TEST 7: Zero keyword matches → fallback default topic
# ---------------------------------------------------------------------------

def test_zero_keywords_fallback():
    msgs = {"messages": [
        {"role": "user", "content": "Hello, how are you doing today?"},
        {"role": "assistant", "content": "I am doing well, thank you!"},
    ]}
    router = make_router(db=make_db(msgs))
    topics = router.route_run("run-001")
    assert len(topics) == 1
    assert topics[0] == "governance-lifecycle-wall"


# ---------------------------------------------------------------------------
# TEST 8: Idempotency — calling route_run twice returns same result
# ---------------------------------------------------------------------------

def test_idempotency():
    router = make_router(db=make_db(TRADING_MSGS))
    result_1 = router.route_run("run-001")
    result_2 = router.route_run("run-001")
    assert result_1 == result_2


# ---------------------------------------------------------------------------
# TEST 9: Very long brick normalization — large bricks don't dominate
# ---------------------------------------------------------------------------

def test_very_long_brick_normalization():
    long_filler = "word " * 10000
    long_content = long_filler + " trading risk regime "
    msgs = {"messages": [{"role": "user", "content": long_content}]}
    router = make_router(db=make_db(msgs))
    result = router.route_run_detailed("run-001")
    assert all(isinstance(v, float) for v in result.raw_scores.values())
    assert all(v < 1000 for v in result.raw_scores.values())  # No explosion


# ---------------------------------------------------------------------------
# TEST 10: Empty run → fallback, never empty list
# ---------------------------------------------------------------------------

def test_empty_run_never_empty_list():
    router = make_router(db=make_db(EMPTY_MSGS))
    topics = router.route_run("run-001")
    assert isinstance(topics, list)
    assert len(topics) >= 1
    assert topics[0] == "governance-lifecycle-wall"


# ---------------------------------------------------------------------------
# TEST 11: Config threshold override forces fallback
# ---------------------------------------------------------------------------

def test_config_threshold_override():
    # Force fallback by requiring an impossibly high raw score threshold (no single-sentence
    # content can achieve 10000 aggregate score), combined with LLM disabled.
    config = RouterConfig(
        weak_score_threshold=10000.0,  # Impossible to reach → triggers LLM path
        enable_llm=False,              # LLM disabled → falls back to deterministic fallback
    )
    router = make_router(db=make_db(TRADING_MSGS), config=config)
    result = router.route_run_detailed("run-001")
    assert result.method == "fallback"
    assert len(result.topics) >= 1


# ---------------------------------------------------------------------------
# TEST 12: Audit event is enforced for LLM spend
# ---------------------------------------------------------------------------

def test_audit_event_enforced():
    gm = make_gm()
    llm = MagicMock()
    llm.generate.return_value = json.dumps({
        "primary_topic": "infra-execution-layer",
        "confidence": 0.88,
        "reasoning": "Infrastructure signals."
    })
    config = RouterConfig(strong_confidence_threshold=0.99, enable_llm=True)
    router = make_router(db=make_db(AMBIGUOUS_MSGS), gm=gm, llm=llm, config=config)
    router.route_run("run-001")
    assert gm._log_audit_event.called


# ---------------------------------------------------------------------------
# TEST 13: LLM disabled mode — no LLM calls ever made
# ---------------------------------------------------------------------------

def test_llm_disabled_no_calls():
    llm = MagicMock()
    config = RouterConfig(strong_confidence_threshold=0.99, enable_llm=False)
    router = make_router(db=make_db(AMBIGUOUS_MSGS), llm=llm, config=config)
    router.route_run("run-001")
    llm.generate.assert_not_called()


# ---------------------------------------------------------------------------
# TEST 14: LLM returns invalid/hallucinated topic — graceful fallback
# ---------------------------------------------------------------------------

def test_llm_invalid_topic_graceful_fallback():
    gm = make_gm()
    llm = MagicMock()
    llm.generate.return_value = json.dumps({
        "primary_topic": "nonexistent-topic-xyz",
        "confidence": 0.95,
        "reasoning": "Hallucinated topic."
    })
    config = RouterConfig(strong_confidence_threshold=0.99, enable_llm=True)
    router = make_router(db=make_db(AMBIGUOUS_MSGS), gm=gm, llm=llm, config=config)
    topics = router.route_run("run-001")
    valid_topics = set(TOPIC_KEYWORD_MAP.keys()) | {"governance-lifecycle-wall"}
    assert topics[0] in valid_topics


# ---------------------------------------------------------------------------
# TEST 15: LLM hard fail response → fallback, does not crash
# ---------------------------------------------------------------------------

def test_llm_hard_fail_graceful():
    gm = make_gm()
    llm = MagicMock()
    llm.generate.return_value = json.dumps({"error": "CONNECTION_FAILED", "status": "HARD_FAIL"})
    config = RouterConfig(strong_confidence_threshold=0.99, enable_llm=True)
    router = make_router(db=make_db(AMBIGUOUS_MSGS), gm=gm, llm=llm, config=config)
    topics = router.route_run("run-001")
    assert len(topics) >= 1


# ---------------------------------------------------------------------------
# TEST 16: _score_bricks internal unit test
# ---------------------------------------------------------------------------

def test_score_bricks_internal():
    router = make_router()
    bricks = [{"content": "trading risk regime trap chaos"}]
    scores = router._score_bricks(bricks)
    assert scores["trading-intelligence-core"] > 0
    assert scores["trading-intelligence-core"] > scores["governance-lifecycle-wall"]


# ---------------------------------------------------------------------------
# TEST 17: _select_primary math correctness
# ---------------------------------------------------------------------------

def test_select_primary_math():
    router = make_router()
    scores = {
        "trading-intelligence-core": 10.0,
        "genai-architecture-core": 5.0,
        "infra-execution-layer": 2.0,
        "governance-lifecycle-wall": 1.0,
    }
    topic, confidence, margin = router._select_primary(scores)
    assert topic == "trading-intelligence-core"
    assert 0.0 < confidence <= 1.0
    assert 0.0 < margin <= 1.0
    assert abs(confidence - 10.0 / 18.0) < 0.01  # ~0.555


# ---------------------------------------------------------------------------
# TEST 18: get_active_topics filters ARCHIVED and LEGACY
# ---------------------------------------------------------------------------

def test_get_active_topics_filters_archived():
    db = make_db()
    db.get_all_topics.return_value = [
        {"id": "trading-intelligence-core", "state": "ACTIVE"},
        {"id": "governance-lifecycle-wall", "state": "ARCHIVED"},
        {"id": "infra-execution-layer", "state": "LEGACY"},
    ]
    router = make_router(db=db)
    active = router.get_active_topics()
    assert "trading-intelligence-core" in active
    assert "governance-lifecycle-wall" not in active
    assert "infra-execution-layer" not in active


# ---------------------------------------------------------------------------
# TEST 19: route_run always returns non-empty list — parametrized invariant
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("msgs", [
    TRADING_MSGS,
    INFRA_MSGS,
    GOVERNANCE_MSGS,
    GENAI_MSGS,
    EMPTY_MSGS,
    {"messages": [{"role": "user", "content": "x"}]},
])
def test_always_non_empty_list(msgs):
    router = make_router(db=make_db(msgs))
    topics = router.route_run("run-001")
    assert isinstance(topics, list)
    assert len(topics) >= 1
    assert all(isinstance(t, str) for t in topics)


# ---------------------------------------------------------------------------
# TEST 20: DB fetch error → graceful fallback, no crash
# ---------------------------------------------------------------------------

def test_db_fetch_error_graceful():
    db = MagicMock()
    db.get_run.side_effect = Exception("DB connection lost")
    router = make_router(db=db)
    topics = router.route_run("run-001")
    assert len(topics) >= 1
