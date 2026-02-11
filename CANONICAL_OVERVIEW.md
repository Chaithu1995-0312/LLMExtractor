# CANONICAL OVERVIEW

## System Name: Nexus

## Purpose
Nexus is a productivity backbone system designed to transform raw conversational data (e.g., ChatGPT exports) into structured, discoverable, and governed knowledge assets. It aims to prevent knowledge drift, ensure consistency, and enable efficient recall and synthesis of technical rules, architectural decisions, and factual statements.

## Core Principles
- **Deterministic Processing**: All ingestion and transformation pipelines are designed to be deterministic, ensuring repeatable results and auditability.
- **Zero-Trust Validation**: Mechanisms are in place to prevent LLM hallucination and ensure that extracted knowledge is verifiably present in source data.
- **Layered Architecture**: Components are organized into distinct layers (Ingestion, Graph, Cognition, Service) with clear responsibilities and interaction boundaries.
- **Knowledge Governance**: Lifecycle management for intents, alert systems for quality issues, and prompt management ensure the integrity and relevance of the knowledge base.
- **Semantic Search**: Utilizes vector embeddings and reranking to provide context-aware and relevant information retrieval.

## High-Level Architecture
The Nexus system can be broadly categorized into the following layers:

### 1. Ingestion Layer
Responsible for taking raw conversational data, splitting it into manageable units, extracting atomic facts and rules, and persisting them.
- **Components**: `nexus.extract.tree_splitter`, `nexus.bricks.extractor`, `nexus.sync.compiler`, `nexus.sync.db`, `nexus.sync.runner`, `nexus.sync.ingest_history`, `nexus.vector.embedder`, `nexus.vector.local_index`, `nexus.walls.builder`.
- **Key Functionality**: Data loading from conversational exports, message filtering based on authority and signal, content chunking into atomic 'bricks', generation of vector embeddings for semantic search, structured extraction of rules/facts using LLMs with zero-trust validation, incremental processing of source data, and building of token-aware 'walls' for large-context processing.

### 2. Graph Layer
Serves as the central knowledge store, representing extracted information as a governed knowledge graph. It enforces data integrity, lifecycle management, and auditability.
- **Components**: `nexus.graph.manager`, `nexus.graph.schema`, `nexus.graph.prompt_manager`, `nexus.graph.projection`, `nexus.governance.alert_manager`, `nexus.sync.db` (for schema).
- **Key Functionality**: Node and edge management, lifecycle transitions for intents (LOOSE, FORMING, FROZEN, SUPERSEDED, KILLED), conflict detection and prevention (e.g., cyclic overrides), versioning and governance of LLM prompts, comprehensive audit logging of system decisions and LLM interactions, and the projection of knowledge onto a visual 'Wall' grid for categorization and overview.

### 3. Cognition Layer
Focuses on higher-order reasoning, synthesis, and quality assurance of the knowledge graph, leveraging LLMs and heuristic mechanisms.
- **Components**: `nexus.cognition.assembler`, `nexus.cognition.coverage_scorer`, `nexus.cognition.coverage_sentinel`, `nexus.cognition.dspy_modules`, `nexus.cognition.prompt_generator`, `nexus.cognition.synthesizer`, `nexus.ask.recall`, `nexus.rerank.orchestrator`, `nexus.rerank.llm_reranker`, `nexus.rerank.cross_encoder`, `nexus.rerank.heuristic`.
- **Key Functionality**: Assembling topic-specific cognition artifacts from retrieved bricks, calculating knowledge coverage scores, detecting structural weaknesses (e.g., semantic redundancy, coverage gaps, orphan bricks, contradictions, analysis without explicit declarations) and emitting actionable alerts, automatically synthesizing relationships between intents to enrich the graph, generating targeted ingestion prompts for knowledge gaps, and a multi-stage reranking pipeline for semantic search results (LLM-based, cross-encoder, heuristic).

### 4. Service Layer (Implied)
While not explicitly defined as a separate Python package, this layer represents the operational endpoints and external interfaces of the Nexus system, such as a CLI or a Gateway for UI interaction and external system integration. (Implied from CLI and Cortex integration points).
- **Components**: `nexus.cli.main`, `services.cortex.api` (implied interaction with Cortex).
- **Key Functionality**: Providing command-line access to Nexus functionalities (extract, wall, sync, ask), and serving as an interface for broader system interaction (e.g., via Cortex for generation and question answering).

## Interaction Flow (Simplified)
1.  **Raw Data Ingestion**: Conversational data is loaded via `nexus.sync.runner`.
2.  **Extraction & Brickification**: `nexus.extract.tree_splitter` breaks down conversations. `nexus.bricks.extractor` creates atomic 'bricks'.
3.  **Embedding**: `nexus.vector.embedder` and `nexus.vector.local_index` create vector representations of bricks.
4.  **LLM Compilation & Validation**: `nexus.sync.compiler` uses `nexus.sync.llm` (with `StructuredIngestLLM`) to extract and validate facts/rules, ensuring zero-trust against hallucination.
5.  **Graph Persistence**: `nexus.sync.db` and `nexus.graph.manager` store bricks, topics, intents, and relationships in the knowledge graph.
6.  **Governance & Alerts**: `nexus.cognition.coverage_sentinel` and `nexus.governance.alert_manager` monitor for knowledge gaps and quality issues.
7.  **Cognitive Synthesis**: `nexus.cognition.assembler` and `nexus.cognition.synthesizer` generate higher-level insights and relationships.
8.  **Query & Recall**: `nexus.ask.recall` uses embeddings and reranking (via `nexus.rerank.orchestrator`) to find relevant bricks.
9.  **Prompt Management**: `nexus.graph.prompt_manager` ensures all LLM prompts adhere to governance policies.
10. **Wall Generation**: `nexus.walls.builder` creates curated summaries for review or further processing.
