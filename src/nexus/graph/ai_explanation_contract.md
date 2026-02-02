# AI Explanation Layer Contract (Design Only)

**Status:** Draft / Locked for Future Implementation
**Role:** Structural Narrator
**Prohibition:** The AI must NEVER decide correctness, ranking, or recall.

## 1. AI Role (Strict)

The AI is a structural narrator, not a judge.
"Explain the map. Never redraw it."

## 2. Input Contract

The AI receives the following JSON payload:

```json
{
  "mode": "explanation_only",
  "user_query": "Trading",
  "recalled_bricks": [
    { "brick_id": "...", "snippet": "..." }
  ],
  "visible_concepts": [
    {
      "concept_id": "concept_trading_systems",
      "anchors": {
        "hard": [...],
        "soft": [...]
      }
    }
  ],
  "graph_edges": [
    {
      "from": "concept_trading_systems",
      "to": "concept_risk_management",
      "type": "depends_on"
    }
  ],
  "anchor_overrides": [
    {
      "concept_id": "...",
      "brick_id": "...",
      "action": "promote",
      "status": "intended"
    }
  ],
  "constraints": {
    "no_new_bricks": true,
    "no_ranking": true,
    "no_writes": true,
    "no_decisions": true
  }
}
```

## 3. Output Contract

The AI response MUST be strictly limited to these sections:

1.  **Structural Overview**: A high-level summary of the visible graph structure.
2.  **Why These Concepts Are Connected**: Explaining the edges (e.g., dependency, hierarchy).
3.  **Human Signals Observed**: Reflecting hard anchors and override intents (e.g., "Humans have marked X as critical").
4.  **Tensions / Open Questions**: Highlighting potential gaps or ambiguities without resolving them.

## 4. Explicit Prohibitions

❌ AI MUST NEVER:

*   Say what is "correct"
*   Promote or reject anchors
*   Suggest adding bricks
*   Override humans
*   Change recall
*   Write files

If the AI attempts any of the above, it constitutes a hard failure of the system invariant.
