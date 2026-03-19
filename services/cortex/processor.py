from __future__ import annotations

from typing import Any, Dict, Optional

from ai.agent import Agent
from services.cortex.orchestrator import Orchestrator


class _NoopExtractor:
    async def run(self, input_data: Dict[str, Any], mode: str = "default") -> Dict[str, Any]:
        return input_data


class _NoopValidator:
    def validate(self, extracted: Dict[str, Any]):
        return extracted


class _NoopGraph:
    def insert(self, valid_data: Dict[str, Any]):
        nodes = [valid_data] if isinstance(valid_data, dict) else [dict(value=valid_data)]
        edges = []
        return nodes, edges


class _NoopStorage:
    async def save(self, nodes, edges):
        return None


class _NoopLLMClient:
    pass


agent = Agent()

orchestrator = Orchestrator(
    extractor=_NoopExtractor(),
    validator=_NoopValidator(),
    graph=_NoopGraph(),
    storage=_NoopStorage(),
    llm_client=_NoopLLMClient(),
    agent=agent,
)


def configure_orchestrator(
    *,
    extractor: Optional[Any] = None,
    validator: Optional[Any] = None,
    graph: Optional[Any] = None,
    storage: Optional[Any] = None,
    llm_client: Optional[Any] = None,
    local_model: Optional[Any] = None,
) -> Orchestrator:
    """
    Optional additive hook for existing runtime to inject real components
    without changing process_input API.
    """
    global orchestrator
    orchestrator = Orchestrator(
        extractor=extractor or _NoopExtractor(),
        validator=validator or _NoopValidator(),
        graph=graph or _NoopGraph(),
        storage=storage or _NoopStorage(),
        llm_client=llm_client or _NoopLLMClient(),
        agent=agent,
        local_model=local_model,
    )
    return orchestrator


async def process_input(data: Dict[str, Any], mode: str = "default"):
    return await orchestrator.process(data, mode=mode)
