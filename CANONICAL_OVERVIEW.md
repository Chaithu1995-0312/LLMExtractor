# Nexus: Canonical Overview
## System Purpose
Nexus is an Agentic Automation and Autonomous Refactoring framework designed to synchronize unstructured conversational data into a structured, executable knowledge graph. It enables recursive extraction of intents, relationship synthesis, and governance-backed prompt generation for autonomous agent behavior.

## Core Pillars
1. **Sync Layer**: Ingests raw historical data, filters for relevance, and materializes "Bricks" (atomic knowledge units).
2. **Graph Layer**: Manages nodes (Source, Scope, Intent) and typed edges, enforcing structural invariants and lifecycle states.
3. **Cognition Layer**: Uses DSPy-powered modules for entity extraction, relationship synthesis, and coverage analysis.
4. **Governance Layer**: Monitors system state, identifies knowledge gaps, and manages prompt safety rails.
5. **Cortex Service**: The operational API and orchestration engine that bridges the graph with external UI and agent runners.

## External Surface Map
| Dependency | Purpose | Failure Mode | Mitigation |
|------------|---------|--------------|------------|
| **Ollama** | Local LLM Inference | Connection timeout / Model crash | Retry logic with exponential backoff; Fallback to mock (dev). |
| **SQLite** | State & Graph Persistence | Disk full / Locked database | WAL mode; Periodic vacuum; Transactional integrity. |
| **OpenAI API**| High-reasoning Synthesis | Rate limit / API Key expiry | Tiered model routing in `LLMRouter`. |
| **Sentence-Transformers** | Vector Embeddings | Out of memory | Local CPU-optimized models (all-MiniLM-L6-v2). |

## Primary Data Schemas & State Logic
### Intent Lifecycle
- **PROPOSED (🔴)**: Newly identified intent, not yet validated.
- **FORMING (🟡)**: Linked to sources, undergoing relationship synthesis.
- **FROZEN (✅)**: Validated, immutable, used in production prompts.
- **KILLED (💀)**: Deprecated or invalidated due to conflict/redundancy.

### Status Transition Logic
`INGEST` -> `PROPOSED` -> `SYNTHESIZE` -> `FORMING` -> `AUDIT` -> `FROZEN`

## Entry Point Mapping
| Module | Entry Point | Type |
|--------|-------------|------|
| **Sync** | `python -m src.nexus.sync` | CLI |
| **Cortex** | `services/cortex/server.py` | REST API |
| **Graph** | `src/nexus/graph/manager.py` | Internal API |
| **Cognition** | `src/nexus/cognition/assembler.py` | Function Call |
| **Governance**| `src/nexus/governance/alert_manager.py` | Event Hook |
