# Nexus Cognitive Memory System — Canonical Overview

## Objective
Nexus is a memory-first cognitive system that ingests conversational data incrementally,
preserves all raw information, and assembles lossless topic-level cognition artifacts
for consumption by LLM agents and UIs.

## Core Capabilities
- Incremental ingestion of new data without reprocessing old data
- Brick-based atomic memory extraction
- Deterministic topic assembly (MODE-1)
- Immutable cognition artifacts
- Graph-based traceability
- UI-friendly tree visualization

## Non-Goals
- No document-level embeddings
- No long-context LLM dependence
- No destructive re-sync
- No hidden inference during ingestion

## Architectural Doctrine
- Compile, don’t summarize
- Recall finds locations, assembly creates knowledge
- Agents consume artifacts, never raw recall
- Old data is never invalidated
