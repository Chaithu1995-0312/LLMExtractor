"""
nexus.orchestration
====================
Cognitive Control Plane — unified query orchestration layer.

Exposes QueryOrchestrator as the single entry point for all user-facing
cognitive queries. This package wraps Graph, Memory, Confidence, and
Escalation subsystems into a single deterministic execution flow.
"""

from nexus.orchestration.query_orchestrator import QueryOrchestrator

__all__ = ["QueryOrchestrator"]
