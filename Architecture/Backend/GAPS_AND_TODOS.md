# Gaps & TODOs

## 1. Critical Technical Debt
- [ ] **Production Server**: `services/cortex/server.py` runs Flask in debug mode. Need Gunicorn/uWSGI wrapper.
- [ ] **Hardcoded Configuration**: Some paths and timeouts are hardcoded. Migrate to `config.py` or `.env`.
- [ ] **Dead Dependencies**: `celery` and `redis` are in `pyproject.toml` but unused. Remove to reduce attack surface.
- [ ] **Error Handling**: `GraphManager` catches generic `Exception` often. Need specific exception types (e.g., `CycleDetectedError`, `LifecycleError`).

## 2. Missing Features (Planned vs Reality)
- [ ] **Vector Integration**: `nexus.vector` exists but is not tightly coupled with `GraphManager`. Graph queries cannot yet filter by semantic similarity efficiently.
- [ ] **L2 Narrator Consumption**: Pulse events are emitted but only logged to stdout/socket. No persistent "Narrative" store exists to aggregate these into a storyline.
- [ ] **UI Visualization**: The `/jarvis/graph-index` endpoint returns raw JSON. A D3.js or Cytoscape frontend is needed for human navigability.

## 3. Operations & Infrastructure
- [ ] **Containerization**: No `Dockerfile` or `docker-compose.yml` (except possibly in root, but not referenced in docs).
- [ ] **Database Migration**: Schema changes (`schema_*.sql`) are manual. Need Alembic or similar migration tool.
- [ ] **Monitoring**: Metrics endpoints exist but no Prometheus scraper configuration.

## 4. Governance
- [ ] **Access Control**: No auth middleware on `CortexAPI`. Anyone with network access can promote/kill nodes.
- [ ] **Cost Limits**: Budget controller exists but hard stops are not fully enforced across all async tasks.
