# GAPS_AND_TODOS

## 1. Critical Gaps (🔴 High Priority)

- [ ] **Security / Auth**: The Cortex API (`server.py`) currently appears to lack robust authentication/authorization mechanisms. API keys or JWTs should be implemented before exposing to a network.
- [ ] **Task Reliability**: Background tasks (`tasks.py`) need a proper queue (e.g., Celery + Redis) instead of potential in-process execution, to ensure reliability during restarts.
- [ ] **Database Migration System**: While schemas exist, a formal migration tool (like Alembic) is not clearly visible. Changing `schema.py` is currently risky.

## 2. Functionality Gaps (🟡 Medium Priority)

- [ ] **UI Feature Parity**: The `Jarvis` UI allows viewing and some editing, but full graph manipulation (adding arbitrary edges, merging nodes visually) is likely incomplete.
- [ ] **Cognitive Feedback Loop**: The "Self-Healing" loop (`CoverageSentinel` -> `PromptGenerator`) exists in code but needs rigorous testing to prove it actually improves graph quality over time without human intervention.
- [ ] **Multi-User Support**: The current design seems single-player or single-tenant.

## 3. Technical Debt (🧪 Low Priority)

- [ ] **Test Coverage**: While tests exist, coverage for edge cases in the `Cognition` layer (which is non-deterministic) is likely low.
- [ ] **Frontend Optimization**: Large graphs might cause performance issues in `CortexVisualizer` or `WallView`. Virtualization or canvas-based rendering may be needed.
