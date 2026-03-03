# Reactive Cloud Cognitive Pipeline: Implementation Document

## Overview
This document outlines the architecture and execution steps for transitioning the Nexus cognitive pipeline into an autonomous, state-driven cloud system. The goal is to process large `conversations.json` exports (e.g., 80MB+) with 100% output reliability and granular visibility.

## 1. Cloud Architecture & Infrastructure
- **Compute**: AWS `g4dn.xlarge` (Recommended) - 16GB RAM, NVIDIA T4 GPU.
- **Database**: External Postgres (RDS `db.t3.micro`).
- **LLM Tiering**:
  - **L1 (Extraction)**: Local Ollama running `phi3:latest`.
  - **L2 (Synthesis)**: OpenAI API.
  - **L3 (Clustering)**: TBD (Configurable).

## 2. Granular Status Tracking (DB Schema)
The following columns must be added to `graph.nodes` and `sync.bricks`:
- `status`: (Enum: `L1_PENDING`, `L1_COMPLETE`, `L2_PENDING`, `L2_COMPLETE`, `L3_PENDING`, `L3_COMPLETE`)
- `l1_started_at`, `l1_completed_at`
- `l2_started_at`, `l2_completed_at`
- `l3_started_at`, `l3_completed_at`

## 3. Implementation Steps

### Step 1: Dynamic Splitting (Batch Preparation)
- **Tool**: `scripts/split_conversations.py`
- **Improvement**: Switch from static "count-based" splitting to **Size-Aware Chunking** (Target: 2MB-5MB per batch).
- **Result**: Predictable RAM usage and timeouts prevention for Ollama.

### Step 2: L1 Extraction (Reactive Phi3 Stream)
- **Logic**: Automatically trigger on new batch detection.
- **Execution**: 
  - Update `status` to `L1_PENDING` and set `l1_started_at`.
  - Call Phi3 via Ollama for concept/intent extraction.
  - Update `status` to `L1_COMPLETE` and set `l1_completed_at`.

### Step 3: L2 Synthesis (State-Driven OpenAI)
- **Logic**: Periodic CRON job (e.g., 30 mins).
- **Filter**: `SELECT * FROM nodes WHERE status = 'L1_COMPLETE'`.
- **Execution**: 
  - Update `status` to `L2_PENDING` and set `l2_started_at`.
  - Call OpenAI for narrative synthesis (bricks).
  - Update `status` to `L2_COMPLETE` and set `l2_completed_at`.

### Step 4: L3 Clustering (Global Organization)
- **Logic**: Periodic CRON job (after L2).
- **Filter**: `SELECT * FROM bricks WHERE status = 'L2_COMPLETE' AND topic_id IS NULL`.
- **Execution**: 
  - Update `status` to `L3_PENDING` and set `l3_started_at`.
  - Run clustering engine to organize bricks into topics.
  - Update `status` to `L3_COMPLETE` and set `l3_completed_at`.

## 4. Key Technical Decisions
- **Sequential L1 Processing**: To protect the 16GB RAM limit, batches are processed one-by-one, not in parallel.
- **State-Check Autonomy**: The system is "Self-Healing." If a job fails, the next CRON cycle sees the "Pending" status and retries.
- **Zero-Local Link**: All data and compute reside in the cloud; the local machine only acts as a trigger/monitor.

## 5. Success Verification
- Run `scripts/validate_nodes.py` to ensure every L1 node has a corresponding L2 brick and L3 topic.
- Verify 100% completion in Jarvis UI "Ingestion" and "Health" pages.
