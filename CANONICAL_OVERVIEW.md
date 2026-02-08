# CANONICAL_OVERVIEW.md

## System Purpose
Nexus is a multi-layered cognitive architecture designed to transform raw conversational data and semi-structured logs into a high-fidelity, queryable knowledge graph. It bridges the gap between raw ingestion and executive decision-making through automated brick extraction, relationship synthesis, and hierarchical scope management.

## Architectural Layers

### 1. Ingestion Layer (`src/nexus/sync`, `src/nexus/bricks`)
Responsible for the "Brickification" of raw data. It captures atomic units of information (Bricks), fingerprints them for deduplication, and stores them in a stateful buffer before promotion to the graph.

### 2. Graph Layer (`src/nexus/graph`)
The system's "Source of Truth." It maintains a SQLite-backed property graph containing:
- **Intents**: Discrete semantic goals or findings.
- **Scopes**: Hierarchical boundaries (Global, Project, Topic).
- **Sources**: Originating agents or users.
- **Edges**: Typed relationships with lifecycle states (Draft, Frozen, Superseded).

### 3. Cognition Layer (`src/nexus/cognition`)
The "Executive Function." Uses DSPy-based modules and LLM synthesis to:
- Assemble disparate bricks into coherent topics.
- Infer latent relationships between Intents.
- Detect conflicts and enforce cross-topic invariants.

### 4. Service Layer (`services/cortex`)
The "Interface." Provides REST and WebSocket gateways (Cortex API) for the UI (Jarvis) and external agents. It handles orchestration, audit logging, and real-time event pulsing.

### 5. UI Layer (`ui/jarvis`)
The "Observer." A React-based visualization suite for graph exploration, node editing, and system monitoring.

## Core Data Flow
1. **Sync**: Raw logs → `NexusCompiler` → `BrickStore`.
2. **Promote**: `Brick` → `GraphManager` → `Intent` (Node).
3. **Synthesize**: `Intents` → `RelationshipSynthesizer` → `Edges`.
4. **Recall**: `User Query` → `RecallEngine` (Vector + Graph) → `Context`.

## Implementation Status Summary
- **Graph Management**: ✅ Stable (SQLite)
- **Ingestion/Sync**: ✅ Stable (Compiler-based)
- **Cognition**: 🟡 Partial (DSPy modules implemented, full self-healing pending)
- **Observability**: ✅ Stable (Audit logging, WebSocket pulsing)
- **UI**: ✅ Stable (Node/Wall visualization)
