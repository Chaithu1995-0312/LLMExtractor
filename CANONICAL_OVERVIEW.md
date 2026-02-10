# CANONICAL_OVERVIEW

## 1. Architectural Summary
Nexus is an Agentic Cognitive Architecture designed to ingest, structure, and synthesize disparate information into a coherent Knowledge Graph. It operates through a multi-stage pipeline: **Ingestion (Sync)**, **Structuring (Graph)**, **Cognition (Synthesis)**, and **Interaction (Cortex/Jarvis)**. The system transitions raw unstructured data into structured "Bricks," which are then woven into a graph of Intents, Sources, and Scopes, enabling high-level reasoning and visualization.

### Core Philosophy
- **Data as Bricks:** Atomic units of information.
- **Graph as Truth:** The source of truth is a directed graph enforcing relationships.
- **Cognition as a Layer:** Higher-order reasoning (synthesis, coverage) runs atop the graph.
- **Agentic Governance:** Automated sentinels monitor and heal the graph.

## 2. System Boundaries & External Surface Map

### External Dependencies
| Dependency | Type | Usage | Failure Mode |
| :--- | :--- | :--- | :--- |
| **OpenAI API** | External Service | LLM for extraction, ranking, synthesis | **CRITICAL:** Pipeline stalls; fallback to Ollama if configured. |
| **Ollama** | Local Service | Local LLM inference (fallback/cost-saving) | **degraded:** High latency or lower quality; system remains functional. |
| **SQLite** | Local Database | Primary persistence for Sync and Graph data | **CRITICAL:** System halt if corrupt or locked. |
| **ChromaDB / Vector Store** | Local Database | Semantic search & embeddings | **PARTIAL:** Recall quality drops; core graph traversal unaffected. |
| **Browser (React)** | Client | UI for visualization and control | **COSMETIC:** Backend continues; user loses visual interactability. |

### Entry Points
| Module | Entry Point | Type | Purpose |
| :--- | :--- | :--- | :--- |
| **Sync** | `src/nexus/sync/runner.py` | CLI | Ingests JSON/History, compiles to Bricks. |
| **Cortex** | `services/cortex/server.py` | HTTP API | Exposes Graph & Cognition capabilities to UI/Agents. |
| **Jarvis** | `ui/jarvis/src/App.tsx` | UI | Frontend dashboard for human-in-the-loop interaction. |
| **CLI** | `src/nexus/cli/main.py` | CLI | Manual administration and debugging. |

## 3. High-Level Data Flow

```mermaid
graph TD
    A[Raw Data (JSON/Chat)] -->|Ingest| B(Sync Engine)
    B -->|Compile| C[Bricks (Atomic Data)]
    C -->|Project| D(Graph Manager)
    D -->|Structure| E[Knowledge Graph (Nodes/Edges)]
    E -->|Synthesize| F(Cognition Layer)
    F -->|Enrich| E
    G[User / Agent] <-->|Query/Mutate| H(Cortex API)
    H <--> E
    H <--> F
```

## 4. Key Subsystems

### 1. Nexus Sync (Ingestion)
**Responsibility:** Raw data normalization and atomization.
- **Input:** JSON exports, chat logs.
- **Process:** Splits content into "Bricks", extracts pointers, assigns fingerprints.
- **Output:** SQLite records (Bricks, Runs, Topics).

### 2. Nexus Graph (Structure)
**Responsibility:** Enforcing structure and relationships.
- **Core Entities:** `Intent`, `Source`, `ScopeNode`.
- **Logic:** Manages node lifecycles (Forming -> Frozen), edge creation, and cycle detection.
- **Persistence:** SQLite (Relational structure of the graph).

### 3. Nexus Cognition (Reasoning)
**Responsibility:** Insight generation and self-correction.
- **Components:** `Assembler`, `Synthesizer`, `CoverageSentinel`.
- **Logic:** Uses LLMs (DSPy) to detect patterns, score topic coverage, and generate prompts.

### 4. Cortex (Service Layer)
**Responsibility:** Orchestration and API gateway.
- **Functions:** Routing, Task Scheduling, Audit Logging.
- **Interface:** REST/WebSocket API for the Jarvis UI.

### 5. Jarvis (UI)
**Responsibility:** Human interface.
- **Features:** Node visualization (`NodeEditor`), Wall projection (`WallView`), Control panel.
- **State:** Zustand store managing modes (Ask, Explore, Visualize).

## 5. Deployment Architecture
- **Monolithic Repo:** All code in one repository.
- **Local-First:** Heavily relies on SQLite and local execution.
- **Hybrid AI:** Switches between Cloud (OpenAI) and Local (Ollama) inference.
