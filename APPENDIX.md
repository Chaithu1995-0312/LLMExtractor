# APPENDIX

## 1. Class → Method → Responsibility Reference

| Class | Method | Responsibility | Used By |
|-------|--------|----------------|---------|
| **GraphManager** | `register_node` | Persist generic node to DB | Internal, `assembler.py` |
| | `register_edge` | Persist generic edge to DB | Internal, `assembler.py` |
| | `promote_node_to_frozen` | **Lifecycle Transition:** Forming -> Frozen | `server.py` (API) |
| | `kill_node` | **Lifecycle Transition:** Any -> Killed | `server.py` (API) |
| | `supersede_node` | **Lifecycle Transition:** Frozen -> Superseded | `server.py` (API) |
| | `get_intents_by_topic` | Retrieve intents for conflict check | `assembler.py` |
| **Assembler** | `assemble_topic` | Orchestrate Topic creation pipeline | `server.py` (API), CLI |
| **CognitiveExtractor** | `forward` | Run DSPy extraction chains | `assembler.py` |
| **CortexAPI** | `assemble` | Wrapper for `assemble_topic` | `server.py` |

## 2. Terminology Glossary

- **Brick:** A raw chunk of conversation.
- **Intent:** A refined, atomic unit of knowledge (Rule, Fact).
- **Topic:** A cluster of Bricks and Intents around a subject.
- **Anchor:** A `FROZEN` intent that overrides conflicting new information.
- **Supersession:** The act of replacing an old `FROZEN` intent with a new one.
- **Monotonicity:** The property that `FROZEN` nodes never change, they only get superseded.

## 3. Directory Structure

```
src/nexus/
├── ask/            # Retrieval logic
├── bricks/         # Ingestion & chunking
├── cognition/      # LLM assembly & extraction
├── graph/          # Graph database & schema
├── vector/         # Embeddings & Index
└── walls/          # (Legacy) Visualization data
services/cortex/    # Flask API
ui/jarvis/          # React Frontend
```
