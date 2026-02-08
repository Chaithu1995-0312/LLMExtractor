# INFERRED_ENHANCEMENTS.md

## 1. Dynamic Graph Projection (Spatial Context)
- **Concept**: Currently, `project_intent` calculates a static Wall grid. An enhancement would be a **Force-Directed Projection** that dynamically adjusts node positions based on the strength of their cognitive relationships (edge weights).
- **Implied Method**: `GraphManager.get_dynamic_layout(focus_node_id)`
- **Status**: 🧪 (Inferred from UI layout requirements)

## 2. Temporal Graph Analysis
- **Concept**: The system tracks `IntentLifecycle`, but lacks a "Timeline View" of how knowledge evolved. An enhancement would be a **Time-Travel Query Engine** to see the graph state at any historical point.
- **Implied Method**: `GraphManager.get_snapshot_at_time(timestamp)`
- **Status**: 🔴 (Inferred from audit log structure)

## 3. Cognitive Conflict Simulation
- **Concept**: Before finalizing a synthesis run, the system could run a "What-If" simulation to predict if new edges will create logical cycles or violate governance rules.
- **Implied Method**: `RelationshipSynthesizer.simulate_forward(intents)`
- **Status**: 🧪 (Inferred from `run_relationship_synthesis` batching)

## 4. Multi-Agent Synthesis Consensus
- **Concept**: Instead of a single LLM pass, use a multi-agent "Debate" to confirm relationships. One agent proposes, another critiques (Red Team), and a third adjudicates.
- **Implied Method**: `JarvisGateway.multi_agent_consensus(payload)`
- **Status**: 🔴 (Inferred from `orchestration.py` retry/verifier logic)

## 5. Automated Brick Pruning (Garbage Collection)
- **Concept**: As Intents are frozen or superseded, the underlying raw Bricks could be archived or deleted to save space and reduce retrieval noise.
- **Implied Method**: `BrickStore.prune_orphaned_bricks()`
- **Status**: 🟡 (Inferred from `scripts/maintenance/prune_bricks.py`)

## 6. Semantic Edge Strength (Weighted Retrieval)
- **Concept**: Edges currently have types but no scalar weights. Adding a `strength` attribute (0.0 to 1.0) would allow the `RecallEngine` to perform more nuanced graph traversals.
- **Implied Method**: `GraphManager.update_edge_weight(edge_id, weight)`
- **Status**: 🟡 (Inferred from DSPy module outputs)
