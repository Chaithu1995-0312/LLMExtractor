# Module Deep Dives

## 1. Rich Ingestion Pipeline (`src/nexus/extract` & `src/nexus/sync`)

The Ingestion Pipeline transforms hierarchical conversation trees into linear, path-stable "Source Runs".

### Control Flow

```mermaid
sequenceDiagram
    participant JSON as Raw Logs
    participant Splitter as TreeSplitter
    participant Runner as Sync Runner
    participant DB as SyncDatabase

    JSON->>Splitter: process_conversation(json)
    Splitter->>Splitter: DFS Traversal
    Splitter->>Splitter: Hash Path (>root>child>child)
    Splitter-->>Runner: List[path_HASH.json] (Linear)
    
    Runner->>DB: register_run(path_hash)
    
    loop Compilation
        Runner->>Compiler: compile_run(path_hash)
        Compiler->>DB: Store Bricks
    end
```

### Key Logic
-   **Path Hashing**: `path_id = hashlib.sha256(">".join(path))` ensures that if a conversation branch remains unchanged, its ID remains stable, allowing for (future) incremental sync.
-   **Rich Content**: The `extract_message` function handles code blocks and tool outputs, preserving them as structured `content_blocks` in the Source Run.

## 2. Governance & Prompt Management (`src/nexus/graph/prompt_manager.py`)

This module enforces safety rails around the system prompts used by the Compiler and Synthesizer.

### Control Flow

```mermaid
sequenceDiagram
    participant Compiler as NexusCompiler
    participant PM as PromptManager
    participant DB as GovernanceDB
    participant Audit as AuditLog

    Compiler->>PM: get_prompt("nexus-compiler-system")
    PM->>DB: SELECT content FROM prompts WHERE slug=?
    
    alt Prompt Found
        DB-->>PM: Content
        PM-->>Compiler: System Prompt
    else Prompt Missing
        PM->>Audit: Log PROMPT_FALLBACK_USED
        PM-->>Compiler: Hardcoded Fallback
    end
    
    alt Prompt Unapproved
        PM->>Audit: Log PROMPT_NOT_APPROVED
        PM-->>Compiler: Warning / Raise Error
    end
```

### Key Logic
-   **Governance Violation**: A specific exception type raised when critical prompts are missing and no fallback is safe.
-   **Versioning**: All prompts are versioned in the DB. The system defaults to the latest version but can request specific ones for reproducibility.

## 3. Cognitive Synthesis Engine (`src/nexus/cognition`)

Background process for discovering relationships.

### Control Flow

```mermaid
sequenceDiagram
    participant API as Cortex API
    participant Syn as Synthesizer
    participant Graph as GraphManager
    participant DSPy as DSPy Module

    API->>Syn: trigger_synthesis()
    Syn->>Graph: Fetch Intents & Existing Edges
    
    loop Batch Processing
        Syn->>DSPy: forward(intents, context=edges)
        DSPy-->>Syn: New Edges
        Syn->>Graph: add_typed_edge()
    end
```
