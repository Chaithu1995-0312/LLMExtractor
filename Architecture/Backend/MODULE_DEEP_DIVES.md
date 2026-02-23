# Module Deep Dives

## 1. Graph Manager (`src/nexus/graph/manager.py`)
**Role**: The "Nervous System" enforcing state integrity and unified storage.

### Core Architecture
The Graph Manager abstracts the underlying Postgres storage (`graph.nodes`, `graph.edges`) into a coherent Object Graph. It is responsible for all state mutations and ensures that no illegal states (e.g., cycles in versioning) are persisted.

### Key Logic: Cycle Detection
Before adding `OVERRIDES` or `SUPERSEDED_BY` edges, the manager performs a DFS traversal to prevent infinite loops.

```mermaid
sequenceDiagram
    participant API as API/Worker
    participant GM as GraphManager
    participant DB as Postgres

    API->>GM: register_edge(A, B, "SUPERSEDED_BY")
    GM->>GM: _check_for_cycle(A, B)
    alt Cycle Detected
        GM-->>API: Error: Cycle Detected (A->B->...->A)
    else Safe
        GM->>DB: INSERT edge (A, B)
        GM->>DB: UPDATE nodes (metadata)
        GM-->>API: Success
    end
```

### Key Logic: Lifecycle Promotion
Promoting a node from `FORMING` to `FROZEN` is a critical boundary crossing.

1.  **Validate Current State**: Node must be `FORMING`.
2.  **Validate Scope (Invariant)**: Node must have an `APPLIES_TO` edge pointing to a Scope.
3.  **Persist**: Update `lifecycle` to `FROZEN`.
4.  **Audit**: Log to `governance.audit_trace`.
5.  **Pulse**: Emit event to L1 Narrator.

## 2. L3 Sage (`src/nexus/cognition/l3_sage.py`)
**Role**: The "Brain" performing strategic audits and high-level reasoning.

### Hybrid Escalation Logic
The Sage uses a "Flash-first, Pro-fallback" strategy to optimize cost vs. intelligence.

```mermaid
sequenceDiagram
    participant Scheduler
    participant Sage as L3 Sage
    participant Router as Escalation Router
    participant LLM_Flash as LLM (Flash)
    participant LLM_Pro as LLM (Pro)

    Scheduler->>Sage: audit_topic_health(TopicID)
    Sage->>Sage: Gather Metrics
    Sage->>Router: route_l3(Prompt)
    Router->>LLM_Flash: Inference
    LLM_Flash-->>Sage: Analysis + Confidence
    
    Sage->>Sage: Compute Confidence (Model + Heuristics)
    
    alt Confidence < Threshold
        Sage->>Router: escalate_l3(Prompt)
        Router->>LLM_Pro: Inference
        LLM_Pro-->>Sage: Deep Analysis
    end
    
    Sage->>Sage: Log Insight & Audit
```

## 3. Postgres Worker (`services/cortex/worker.py`)
**Role**: The "Muscle" ensuring reliable, atomic execution of asynchronous tasks.

### Transactional Task Execution
The worker couples the *Task State* (Queue) and *Graph Mutation* (Business Logic) into a single ACID transaction. This ensures that if the business logic fails, the task is not marked as complete, and if the task update fails, the graph is not mutated.

```mermaid
sequenceDiagram
    participant Worker
    participant DB as Postgres Queue
    participant Handler as Task Handler

    loop Polling
        Worker->>DB: BEGIN TRANSACTION
        Worker->>DB: SELECT ... FOR UPDATE SKIP LOCKED
        
        opt No Task
            Worker->>DB: ROLLBACK
        end
        
        Worker->>DB: UPDATE status='running'
        
        par Execute
            Worker->>Handler: run(payload)
            Handler->>DB: INSERT/UPDATE Graph Nodes (Same TX)
        and
            Worker->>DB: UPDATE status='completed'
        end
        
        alt Success
            Worker->>DB: COMMIT
        else Error
            Worker->>DB: ROLLBACK
            Worker->>DB: (New TX) UPDATE status='failed', retry++
        end
    end
```
