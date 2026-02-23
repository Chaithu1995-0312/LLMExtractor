# CANONICAL_OVERVIEW

**System Name:** Nexus Cognitive Architecture (NCA)
**Version:** 0.8.2 (Inferred)
**Primary Pattern:** Event-Sourced Graph RAG with Agentic Governance
**Language:** Python 3.10+ (Backend), TypeScript/React (Frontend)

## 1. Architectural Synopsis
Nexus is a **Cognitive Graph Engine** designed to ingest raw unstructured data (conversations, code, logs), atomize it into "Bricks", and synthesize these into a queryable, versioned Knowledge Graph. It distinguishes itself from standard RAG by enforcing **Monotonic State Transitions** (Loose → Forming → Frozen) and **Cryptographic Provenance** (Source → Brick → Intent).

The system operates on three planes:
1.  **Ingestion Plane (Sync):** Deterministic compiler that turns linear streams into content-addressable "Bricks".
2.  **Cognition Plane (Graph):** Stateful graph manager that promotes Bricks into Intents, enforcing logical consistency and conflict resolution.
3.  **Governance Plane (Cortex):** API gateway and observability layer that creates an audit trail for every AI decision.

## 2. Core Domain Models

### Data Hierarchy
*   **Source Run (`src/nexus/sync`):** An immutable linear tape of raw input (e.g., chat logs).
*   **Brick (`src/nexus/bricks`):** The atomic unit of information. A content-addressed, immutable fragment extracted from a Source Run.
*   **Intent (`src/nexus/graph`):** A synthesized, mutable node in the Knowledge Graph representing a distinct concept or fact derived from Bricks.
*   **Edge (`src/nexus/graph`):** Typed relationships (DERIVED_FROM, OVERRIDES, SUPERSEDED_BY) defining the topology of knowledge.

### State Transitions (The "Lifecycle")
The system enforces a strict lifecycle for Knowledge Nodes (Intents):
1.  **LOOSE (🟡):** Freshly ingested or inferred. Volatile.
2.  **FORMING (✅):** Validated by an agent or heuristic. Stable but mutable.
3.  **FROZEN (🔒):** Cryptographically locked. Cannot be changed, only Superseded.
4.  **SUPERSEDED (❌):** Replaced by a newer FROZEN node. Retained for history.
5.  **KILLED (💀):** Explicitly rejected by Governance.

## 3. External Surface Map

### 3rd Party Dependencies & Failure Modes
| Dependency | Usage | Risk Profile | Failure Mode | Mitigation |
| :--- | :--- | :--- | :--- | :--- |
| **PostgreSQL** | Primary Truth Store (Nodes, Edges) | HIGH | Connection Timeout / Corruption | `nexus.db.postgres` generic adapter with retry logic (implied). |
| **SQLite** | Local/Dev Graph Store | MED | File Lock / Corruption | `GraphManager` handles WAL mode (implied). |
| **Ollama / LLM** | Cognition (DSPy Modules) | HIGH | Hallucination / Timeout / Rate Limit | `nexus.cognition.dspy_modules` with structured output enforcement. |
| **Redis** | Celery Broker / Cache | LOW | Queue Overflow | Async tasks (`services.cortex.tasks`) degrade to sync if missing. |
| **Socket.IO** | Real-time Frontend Updates | LOW | Disconnect | `ui/jarvis` handles reconnection and delta sync. |

## 4. System Boundaries

### Entry Points
*   **CLI (`src/nexus/cli`):** Developer tools for manual ingestion and graph maintenance.
*   **API (`services/cortex`):** REST + WebSocket interface for the UI and external agents.
*   **FileSystem (`data/`):** Watched directories for auto-ingestion of source logs.

### Exit Points
*   **Audit Log (`governance.audit_trace`):** Immutable append-only log of all state changes.
*   **Graph Snapshots:** JSON exports of the current knowledge state.
*   **Cognitive Artifacts:** Synthesized JSON documents describing assembled topics.
