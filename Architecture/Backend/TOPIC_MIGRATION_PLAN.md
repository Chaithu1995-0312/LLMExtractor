# Topic Migration Plan
## From: 1-Topic Broadcast → 4-Topic Routed Architecture

**Document Version:** 1.0  
**Status:** APPROVED FOR EXECUTION  
**Created:** 2026-02-25  
**Invariant:** No direct `UPDATE topic_id` on sync.bricks. Ever.

---

## 1. Current State (Baseline)

| Metric | Value |
|---|---|
| Total bricks | 4,550 |
| Active topics | 1 (`nexus-server-sync`) |
| Topic distribution | 100% broadcast |
| Architecture | Deterministic compiler, broadcast mode |
| Risk | Re-ingestion multiplies brick count |

**Architecture label:** `Broadcast / Flat`

---

## 2. Target State

| New Topic ID | Domain | Est. % of bricks |
|---|---|---|
| `trading-intelligence-core` | Trading strategy, regime, risk, Ultron | ~40% |
| `genai-architecture-core` | Jarvis, Claude, multi-agent, cognition | ~25% |
| `infra-execution-layer` | Lambda, DynamoDB, ECS, PGWorker | ~20% |
| `governance-lifecycle-wall` | Nexus meta, brick lifecycle, audit | ~15% |

**Architecture label:** `Routed / Segmented`

**Bootstrap topic `nexus-server-sync` state:** LEGACY → ARCHIVED

---

## 3. Migration Phases

### Phase 0 — Prerequisites (Before Any Migration)

- [ ] All 25 unit tests passing (`pytest tests/unit/test_topic_router.py`)
- [ ] `router.py` imported cleanly (`python -c "from nexus.sync.router import TopicRouter"`)
- [ ] `runner.py` imports validated
- [ ] Backup of current sync DB state taken
- [ ] `simulate_topic_router.py` run confirms expected domain split

**Command to validate router import:**
```bash
python -c "from nexus.sync.router import TopicRouter, RouterConfig, TOPIC_KEYWORD_MAP; print('OK')"
```

---

### Phase 1 — Create 4 New Topics in DB

Run this SQL against the sync database:

```sql
-- Create 4 new domain topics
INSERT INTO sync.topics (id, display_name, definition, state, created_at)
VALUES
  ('trading-intelligence-core',
   'Trading Intelligence Core',
   '{"scope_description": "Trading strategy, regime logic, risk management, Ultron risk governor, execution doctrine, prop trading rules."}',
   'ACTIVE',
   NOW()),

  ('genai-architecture-core',
   'GenAI Architecture Core',
   '{"scope_description": "Multi-agent architecture, Jarvis orchestration, Claude/Gemini routing, confidence engine, escalation logic, cognition layers."}',
   'ACTIVE',
   NOW()),

  ('infra-execution-layer',
   'Infrastructure Execution Layer',
   '{"scope_description": "AWS Lambda, DynamoDB, ECS, EventBridge, PGWorker, Postgres transactions, Docker, Redis, queue architecture."}',
   'ACTIVE',
   NOW()),

  ('governance-lifecycle-wall',
   'Governance Lifecycle Wall',
   '{"scope_description": "Nexus brick lifecycle, audit invariants, wall governance, frozen/superseded/killed states, extraction-first doctrine, compiler trace."}',
   'ACTIVE',
   NOW());
```

**Add `state` column if not already present:**
```sql
ALTER TABLE sync.topics
ADD COLUMN IF NOT EXISTS state VARCHAR(32) DEFAULT 'ACTIVE';

-- Mark bootstrap topic as LEGACY (do NOT delete yet)
UPDATE sync.topics SET state = 'LEGACY' WHERE id = 'nexus-server-sync';
```

**Verification:**
```sql
SELECT id, state FROM sync.topics ORDER BY created_at;
-- Expected: 5 rows, nexus-server-sync = LEGACY, 4 new = ACTIVE
```

---

### Phase 2 — Simulation Dry-Run

Before any re-compilation, run the TopicRouter simulation to validate domain separation:

```bash
python scripts/simulate_topic_router.py
```

Expected output format:
```
Topic Distribution (estimated):
  trading-intelligence-core  : 38.2%  (1,738 bricks)
  genai-architecture-core    : 24.1%  (1,097 bricks)
  infra-execution-layer      : 22.4%  (1,019 bricks)
  governance-lifecycle-wall  : 15.3%  (  696 bricks)
```

**Gate:** If any topic < 5% → review keyword map before proceeding.

---

### Phase 3 — Re-Compile Historical Runs Into New Topics

**CRITICAL:** Do NOT modify existing bricks. Compile fresh into new topics.

Use `run_sync` with `routing_mode="router"`:

```python
from nexus.sync.runner import run_sync, ROUTER_MODE_ROUTER
from nexus.sync.router import RouterConfig

run_sync(
    input_json="path/to/conversations.json",
    output_dir="output/",
    rebuild_index=False,      # Do NOT truncate — append mode
    routing_mode=ROUTER_MODE_ROUTER,
    router_config=RouterConfig(
        enable_llm=False,     # Phase 3: deterministic only first
    ),
)
```

**This will:**
1. Re-read all source runs
2. Route each run via TopicRouter (keyword scoring, no LLM)
3. Compile bricks into `trading-intelligence-core`, `genai-architecture-core`, etc.
4. Leave `nexus-server-sync` bricks **untouched** (still exist as LEGACY snapshot)

**Monitor:**
```sql
SELECT topic_id, COUNT(*) FROM sync.bricks
GROUP BY topic_id ORDER BY count DESC;
```

---

### Phase 4 — LLM-Assisted Disambiguation (Optional)

After deterministic Phase 3, run LLM routing for ambiguous runs:

```python
run_sync(
    input_json="path/to/conversations.json",
    output_dir="output/",
    rebuild_index=False,
    routing_mode=ROUTER_MODE_ROUTER,
    router_config=RouterConfig(
        enable_llm=True,
        llm_min_confidence=0.65,
        strong_confidence_threshold=0.75,
    ),
)
```

**Gate:** LLM invocation rate should be < 20% of runs. If > 20%, revisit keyword map.

---

### Phase 5 — Verification

```sql
-- Brick count per new topic
SELECT topic_id, COUNT(*) as brick_count,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) as pct
FROM sync.bricks
WHERE topic_id != 'nexus-server-sync'
GROUP BY topic_id
ORDER BY brick_count DESC;

-- Ensure no topic is empty
SELECT topic_id FROM sync.topics
WHERE state = 'ACTIVE'
AND id NOT IN (SELECT DISTINCT topic_id FROM sync.bricks);
-- Expected: 0 rows (all active topics have bricks)

-- Duplicate fingerprint check
SELECT fingerprint, COUNT(*) FROM sync.bricks
GROUP BY fingerprint HAVING COUNT(*) > 3
ORDER BY count DESC LIMIT 20;
```

**Gates before Phase 6:**
- [ ] All 4 new topics have bricks
- [ ] No topic has fewer than 200 bricks
- [ ] Duplicate fingerprint rate < 15%
- [ ] `governance-lifecycle-wall` contains meta/lifecycle content

---

### Phase 6 — Archive Bootstrap Topic

Only after Phase 5 gates are met:

```sql
UPDATE sync.topics SET state = 'ARCHIVED' WHERE id = 'nexus-server-sync';
```

**INVARIANT:** Do NOT delete `nexus-server-sync` bricks. They are the historical snapshot.  
**INVARIANT:** `ARCHIVED` topics cannot accept new compilations (enforce in `compiler.py`).

---

### Phase 7 — Activate Router Mode Permanently

Update `__main__.py` or your deployment config:

```python
# Before:
run_sync(input_json, output_dir)

# After:
from nexus.sync.runner import run_sync, ROUTER_MODE_ROUTER
run_sync(input_json, output_dir, routing_mode=ROUTER_MODE_ROUTER)
```

---

## 4. Rollback Plan

If any phase fails, rollback is safe because:
- Existing `nexus-server-sync` bricks are **never deleted**
- New topic bricks can be purged without affecting LEGACY snapshot

```sql
-- Emergency rollback: remove new topic bricks
DELETE FROM sync.bricks
WHERE topic_id IN (
  'trading-intelligence-core',
  'genai-architecture-core',
  'infra-execution-layer',
  'governance-lifecycle-wall'
);

-- Re-activate bootstrap
UPDATE sync.topics SET state = 'ACTIVE' WHERE id = 'nexus-server-sync';
UPDATE sync.topics SET state = 'ARCHIVED'
WHERE id IN (
  'trading-intelligence-core',
  'genai-architecture-core',
  'infra-execution-layer',
  'governance-lifecycle-wall'
);
```

---

## 5. Topic Lifecycle State Machine

```
EXPERIMENTAL → ACTIVE → FROZEN → ARCHIVED
                            ↑
                          LEGACY (bootstrap artifact only)
```

| State | Accepts new runs? | Graph queries? | Can compile? |
|---|---|---|---|
| ACTIVE | ✅ | ✅ | ✅ |
| FROZEN | ❌ | ✅ | ❌ |
| ARCHIVED | ❌ | ✅ (read-only) | ❌ |
| LEGACY | ❌ | ✅ (read-only) | ❌ |
| EXPERIMENTAL | ✅ (test only) | ✅ | ✅ |

---

## 6. Governance API Additions Required

These methods should be added to `SyncDatabase` or a new `TopicGovernanceManager`:

```python
def update_topic_state(topic_id: str, new_state: str) -> None:
    """ACTIVE | FROZEN | ARCHIVED | LEGACY | EXPERIMENTAL"""

def list_active_topics() -> List[Dict]:
    """Returns only ACTIVE topics eligible for routing."""

def get_topic_distribution_metrics() -> Dict[str, int]:
    """Returns brick count per topic for monitoring."""
```

---

## 7. Key Invariants (Never Violate)

1. **No `UPDATE topic_id` on `sync.bricks`** — ever
2. **No direct DB writes in TopicRouter** — advisory only
3. **ARCHIVED topics cannot compile** — enforce in compiler
4. **Every LLM call must emit audit event** — via GraphManager
5. **Router must always return non-empty list** — fallback to `governance-lifecycle-wall`
6. **LEGACY bricks are the historical snapshot** — never delete

---

## 8. Files Changed in This Migration

| File | Change |
|---|---|
| `src/nexus/sync/router.py` | NEW — TopicRouter class |
| `src/nexus/sync/runner.py` | UPDATED — routing_mode parameter, router integration |
| `tests/unit/test_topic_router.py` | NEW — 25 unit tests (all passing) |
| `scripts/simulate_topic_router.py` | NEW — dry-run simulation on 4,550 bricks |
| `Architecture/Backend/TOPIC_MIGRATION_PLAN.md` | NEW — this document |

---

## 9. Expected Final State

```
Sync Runner
   ↓ (routing_mode="router")
TopicRouter (Hybrid: keyword + optional LLM)
   ↓ (returns topic ID)
NexusCompiler (pure deterministic, unchanged)
   ↓
GraphManager (audit enforced)
   ↓
4 domain topics, 1 ARCHIVED legacy
```

**Broadcast model eliminated.**  
**Brick multiplication risk eliminated.**  
**Semantic partitioning achieved.**
