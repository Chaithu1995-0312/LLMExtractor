# Canonical Architectural Overview

## System Identity
**Name:** Nexus Cognitive Architecture (v3)
**Primary Function:** Autonomous Knowledge Synthesis & Governance Engine
**Core Philosophy:** "Zero-Trust Ingestion, Monotonic Truth, Budget-Aware Cognition"

## High-Level Architecture
Nexus is a **local-first, hybrid-cloud cognitive engine** that transforms unstructured conversation logs into a rigorous, queryable Knowledge Graph. It distinguishes itself from standard RAG systems by enforcing strict **lifecycle governance** on knowledge artifacts ("Bricks") and using a **multi-tier cognitive gateway** to manage inference costs.

### The 4-Layer Stack

1.  **Ingestion Layer (The "Digestive System")**
    *   **Responsibility:** Raw log parsing, structural scanning, and "Brick" materialization.
    *   **Key Component:** `NexusCompiler`
    *   **Mechanism:** Uses deterministic LLM pointers to extract verbatim quotes. **Zero-Trust Validation** rejects any extraction that does not match the source text byte-for-byte.

2.  **Graph Layer (The "Long-Term Memory")**
    *   **Responsibility:** Storage of Bricks, Intents, Sources, and Scopes.
    *   **Key Component:** `GraphManager`
    *   **Data Structure:** Unified Node/Edge Graph (SQLite).
    *   **Governance:** Enforces the **Lifecycle State Machine** (IMPROVISE → FORMING → FROZEN → KILLED).

3.  **Cognition Layer (The "Synthesizer")**
    *   **Responsibility:** Higher-order reasoning, relationship discovery, and answering.
    *   **Key Component:** `CortexAPI` & `JarvisGateway`
    *   **Mechanism:**
        *   **L1 (Pulse):** Local/Free (Ollama/Llama3) for status updates.
        *   **L2 (Voice):** Cloud/Standard (Claude-3.5) for user Q&A.
        *   **L3 (Sage):** Cloud/Reasoning (o1/GPT-4o) for deep structural analysis.

4.  **Interface Layer (The "Control Plane")**
    *   **Responsibility:** Visualization and Interaction.
    *   **Key Component:** `Jarvis UI` (React)
    *   **Features:** Wall View (Graph interaction), Chat (Agent interface).

## Core Workflows

### 1. The Compiler Loop (Ingest)
1.  **Scan:** `NexusCompiler` loads raw conversation JSON.
2.  **Point:** LLM identifies relevant segments ("Pointers") based on Topic Definitions.
3.  **Validate:** `_materialize_brick` verifies the pointer matches source text exactly.
4.  **Persist:** Validated segments are saved as "Bricks" (State: IMPROVISE).

### 2. The Promotion Cycle (Governance)
1.  **Form:** Bricks are grouped into "Intents".
2.  **Freeze:** Humans or high-confidence agents promote Intents to FROZEN state.
    *   *Invariant:* Frozen nodes cannot be modified, only Superseded.
3.  **Supersede:** New information renders old facts obsolete. A "SUPERSEDED_BY" edge is created.

### 3. The Retrieval Flow (Recall)
1.  **Search:** Vector Search (`LocalVectorIndex`) finds relevant Bricks.
2.  **Expand:** Graph Traversal (`GraphManager`) pulls connected context (Sources, Scopes).
3.  **Synthesize:** `CortexAPI` routes the context to the appropriate model via `JarvisGateway`.

## Technology Stack
*   **Language:** Python 3.10+ (Backend), TypeScript (Frontend)
*   **Database:** SQLite (Relational + Graph + Vector storage via blob/JSON)
*   **Vector Search:** FAISS (Local), `sentence-transformers/all-MiniLM-L6-v2`
*   **LLM Orchestration:** DSPy (Modules), LiteLLM (Proxy)
*   **Frontend:** React, Vite, Tailwind
