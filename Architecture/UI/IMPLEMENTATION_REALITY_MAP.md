# IMPLEMENTATION_REALITY_MAP

This document maps the UI components and backend endpoints to their current implementation status.

## Feature Parity Map

| Category | Feature | Frontend Component | Backend Endpoint | Status | Notes |
|----------|---------|--------------------|------------------|--------|-------|
| **Search** | Semantic Brick Recall | `App.tsx` (Ask Mode) | `/jarvis/ask-preview` | ✅ | Fully functional preview mode. |
| **Search** | GenAI Augmented Search | `App.tsx` (AI+ Toggle) | `/jarvis/ask-preview?use_genai=true` | ✅ | Backend handles LLM orchestration. |
| **Graph** | Global Node Index | `WallView.tsx` | `/jarvis/graph-index` | ✅ | Primary entry point for knowledge. |
| **Graph** | Graph Visualization | `CortexVisualizer.tsx` | `/jarvis/graph-index` | ✅ | Uses Cytoscape + Dagre. |
| **Graph** | Layout Persistence | `App.tsx` (Graph View) | N/A | 🟡 | Positions are kept in local component state. |
| **Lifecycle** | Promote Node | `NodeEditor.tsx` | `/jarvis/node/promote` | ✅ | Transitions node to FROZEN. |
| **Lifecycle** | Kill Node | `NodeEditor.tsx` | `/jarvis/node/kill` | ✅ | Marks node as KILLED. |
| **Lifecycle** | Supersede Node | `NodeEditor.tsx` | `/jarvis/node/supersede` | ✅ | Links old node to new replacement. |
| **Lifecycle** | Anchor/Reject | `ControlStrip.tsx` (Implied) | `/jarvis/anchor` | 🟡 | Logic exists in backend, UI wiring partial. |
| **Cognition** | Topic Assembly | `ControlPanel.tsx` | `/cognition/assemble` | ✅ | Triggered via "Terminal" UI. |
| **Cognition** | Relationship Synthesis| `ControlPanel.tsx` | `/cognition/synthesize` | ✅ | Triggered via "Terminal" UI. |
| **Discovery** | Prompt Management | `ControlPanel.tsx` | `/jarvis/prompts` | ✅ | Lists system prompts and scores. |
| **Audit** | Forensic Trail | `AuditPanel.tsx` | `/api/audit/events` | ✅ | Real-time polling (5s interval). |
| **Audit** | Run Details | N/A | `/api/runs/<run_id>` | 🔴 | Endpoint exists; no dedicated UI view. |
| **Sync** | Background Sync | `ControlPanel.tsx` | `/tasks/sync` | ✅ | Triggered manually from UI. |

## Entry Point Mapping

| Module | Entry Type | Destination | Authority |
|--------|------------|-------------|-----------|
| **Recall Engine** | API (GET) | `/jarvis/ask-preview` | Read-Only |
| **Graph Manager** | API (POST) | `/jarvis/node/*` | Write-Authoritative |
| **Cortex Worker** | Celery / Event | `tasks.py` | Transactional |
| **Jarvis UI** | User Action | `App.tsx` | Orchestration |

## Status Legend
- ✅ **Implemented**: Fully functional and wired.
- 🟡 **Partial**: Logic exists in one layer but missing full integration.
- 🔴 **Missing**: Planned or backend-only; no UI exposure.
- 🧪 **Mocked**: UI exists but uses placeholder/local data.
