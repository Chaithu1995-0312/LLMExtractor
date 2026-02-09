# Nexus: File Index

## Sync Module (`src/nexus/sync/`)
| File | Class → Methods | Risk |
|------|-----------------|------|
| `compiler.py` | `NexusCompiler`: `compile_run` (Main flow), `_llm_extract_pointers` (Extractive), `_materialize_brick` (DB Write). | MED/HIGH |
| `db.py` | `SyncDatabase`: `create_topic` (Schema), `save_brick` (State), `get_bricks_for_topic` (Read). | MED |
| `llm.py` | `LLMClient`: `generate` (External API), `_call_ollama` (Local API). | HIGH |
| `runner.py` | `run_sync` (Orchestrator): Top-level sync execution. | MED |

## Graph Module (`src/nexus/graph/`)
| File | Class → Methods | Risk |
|------|-----------------|------|
| `manager.py` | `GraphManager`: `register_node` (Write), `register_edge` (Write), `promote_node_to_frozen` (Lifecycle). | HIGH |
| `projection.py` | `project_intent` (Pure): Transforms graph nodes into UI/Wall structures. | LOW |
| `prompt_manager.py`| `PromptManager`: `get_prompt` (Read), `save_prompt` (Write/Gov). | MED |
| `validation.py` | `run_full_validation` (Read): Ensures no cycles/orphans. | LOW |

## Cognition Module (`src/nexus/cognition/`)
| File | Class → Methods | Risk |
|------|-----------------|------|
| `assembler.py` | `assemble_topic` (Orchestrator): RAG + DSPy synthesis pipeline. | HIGH |
| `dspy_modules.py` | `CognitiveExtractor`: `forward` (LLM), `RelationshipSynthesizer`: `forward` (LLM). | HIGH |
| `coverage_scorer.py`| `CoverageScorer`: `compute_score` (State Analytics). | LOW |
| `prompt_generator.py`| `PromptGenerator`: `generate_prompts` (Autonomous Write). | HIGH |

## Governance Module (`src/nexus/governance/`)
| File | Class → Methods | Risk |
|------|-----------------|------|
| `alert_manager.py` | `AlertManager`: `persist_alert` (State), `resolve_alert` (Lifecycle), `_transition_state` (Invariants). | MED |

## Cortex Service (`services/cortex/`)
| File | Class → Methods | Risk |
|------|-----------------|------|
| `api.py` | `CortexAPI`: `route` (Gateway), `ask_preview` (Read), `synthesize` (Task Trigger). | HIGH |
| `server.py` | Flask App: Maps REST endpoints to `CortexAPI` methods. | MED |
| `tasks.py` | Celery/Async Tasks: Wrappers for sync/synthesis background jobs. | MED |

## Bricks Module (`src/nexus/bricks/`)
| File | Class → Methods | Risk |
|------|-----------------|------|
| `brick_store.py` | `BrickStore`: `get_brick_text` (Read), `get_brick_metadata` (Read). | LOW |
| `resolver.py` | `UserTriggeredResolver`: `resolve` (Logic): Matches user input to bricks. | MED |

## Vector Module (`src/nexus/vector/`)
| File | Class → Methods | Risk |
|------|-----------------|------|
| `embedder.py` | `VectorEmbedder`: `embed_query` (ML Inference), `_rewrite_with_llm` (LLM). | MED |
| `local_index.py` | `LocalVectorIndex`: `search` (Similarity), `save` (Disk). | MED |
