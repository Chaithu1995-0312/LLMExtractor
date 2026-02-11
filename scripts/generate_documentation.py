
import json
import os
from collections import defaultdict

# Global variable to store parsed intelligence
code_intelligence = {}

# --- Helper Functions for Document Generation ---

def get_all_classes_and_methods():
    all_classes_methods = {}
    for filepath, classes in code_intelligence.items():
        for class_name, methods in classes.items():
            all_classes_methods[f"{filepath}::{class_name}"] = {
                "class_name": class_name,
                "methods": methods
            }
    return all_classes_methods

def generate_canonical_overview():
    doc = """# CANONICAL_OVERVIEW.md

## 1. System Overview

This document provides a high-level architectural overview of the Nexus system, focusing on its core components for Agentic Automation and Autonomous Refactoring. The system is designed around a knowledge graph (`nexus.graph`), cognitive modules (`nexus.cognition`), synchronization mechanisms (`nexus.sync`), and vector embeddings (`nexus.vector`) to process, understand, and act upon code and system-level information.

## 2. External Surface Map

### 2.1. Third-Party Dependencies (APIs, SDKs)

*   **Ollama (Local LLM)**:
    *   **Description**: Used for local large language model inference, primarily for zero and low-cost tolerance LLM requests.
    *   **Failure Modes**: 
        *   **Connection Refused**: Ollama server not running or incorrect host/port configuration.
        *   **Timeout**: LLM inference takes too long.
        *   **Empty Response**: Ollama returns an empty or malformed response.
        *   **Resource Exhaustion**: Local machine lacks sufficient RAM/GPU for model execution.
    *   **Referenced In**: `src/nexus/sync/llm.py`

*   **OpenAI API (GPT Models)**:
    *   **Description**: Used for high-cost tolerance and advanced LLM requests, as well as for query expansion in vector embeddings.
    *   **Failure Modes**: 
        *   **API Key Missing/Invalid**: Authentication failure.
        *   **Rate Limiting**: Exceeding allowed requests per minute/second.
        *   **Network Issues**: Inability to reach OpenAI endpoints.
        *   **Model Errors**: Issues with specific GPT models (e.g., `gpt-4o-mini`, `gpt-4o`).
    *   **Referenced In**: `src/nexus/sync/llm.py`, `src/nexus/vector/embedder.py`

*   **Sentence-Transformers (Embeddings)**:
    *   **Description**: Python library for generating sentence and text embeddings, specifically using pre-trained models like `all-MiniLM-L6-v2`.
    *   **Failure Modes**: 
        *   **Model Not Downloaded**: Initial download failure or corruption.
        *   **Resource Limits**: High memory usage during embedding of large text batches.
        *   **Import Error**: Library not installed.
    *   **Referenced In**: `src/nexus/vector/embedder.py`

*   **sqlite3 (Database)**:
    *   **Description**: Python
\"s built-in SQLite database interface for local persistent storage of the knowledge graph.
    *   **Failure Modes**: 
        *   **Database Locked**: Concurrent access issues.
        *   **Corruption**: Database file integrity compromised.
        *   **Schema Mismatch**: Changes in schema not properly migrated.
    *   **Referenced In**: `src/nexus/graph/manager.py`, `src/nexus/sync/db.py`

*   **DSPy (Declarative Self-improving Language Programs)**:
    *   **Description**: Framework for programming LLMs, used for tasks like relationship synthesis.
    *   **Failure Modes**: 
        *   **Module Configuration**: Incorrect setup of DSPy modules or predictors.
        *   **LLM Integration**: Underlying LLM failures (as described above for Ollama/OpenAI).
        *   **Prompt Engineering Issues**: Poorly designed prompts leading to bad outputs.
    *   **Referenced In**: `src/nexus/cognition/dspy_modules.py`, `src/nexus/cognition/synthesizer.py`

### 2.2. Core Data Flows (High-Level)

1.  **Ingestion**: Raw text/code -> `nexus.extract` (Tree Splitter) -> `nexus.vector` (Embedder) -> `nexus.sync` (Compiler/DB) -> Graph Nodes (`nexus.graph`).
2.  **Cognition**: Intents/Nodes in Graph -> `nexus.cognition` (Synthesizer, Prompt Generator) -> `nexus.sync.llm` (LLM Routing) -> Relationships/Edges in Graph (`nexus.graph`).
3.  **Query/Rerank**: User Query -> `nexus.vector` (Embedder/Query Rewrite) -> `nexus.rerank` (LLM Reranker/Heuristic) -> `nexus.ask` (Recall) -> Ranked Results.
4.  **Governance/Audit**: All significant actions (`nexus.graph.manager`) -> Audit Logs (`phase3_audit_trace.jsonl`).

---

"""
    return doc

def generate_implementation_reality_map():
    doc = """# IMPLEMENTATION_REALITY_MAP.md

## 1. Method Implementation Status

This section maps each method to its current implementation status within the Nexus system.

### Status Classification:
*   ✅ **Implemented**: Fully functional and tested.
*   🟡 **Partial**: Partially implemented, missing features, or known limitations.
*   🔴 **Missing**: Declared or inferred, but not yet implemented.
*   🧪 **Mocked**: Uses a mock implementation for testing or temporary development.

"""
    all_classes_methods = get_all_classes_and_methods()
    for class_path, class_info in sorted(all_classes_methods.items()):
        class_name = class_info["class_name"]
        doc += f"\n### `Class: {class_name}` (`{os.path.dirname(class_path).replace("src/", "")}`)\n\n"
        for method_name, method_details in sorted(class_info["methods"].items()):
            status = "✅ Implemented" # Default assumption for existing code
            if "_mock_response" in method_details["calls"] or "LLM_MOCK_INGEST" in method_details["inputs_outputs"]:
                status = "🧪 Mocked"
            elif "TODO" in method_details["responsibility"] or "TODO" in method_details["inputs_outputs"]:
                status = "🟡 Partial"
            elif method_details["responsibility"] == "🔴 MISSING_FROM_CONTEXT" and method_details["inputs_outputs"] == "🔴 MISSING_FROM_CONTEXT":
                status = "🔴 Missing"
            
            doc += f"*   `{method_name}`: {status} - {method_details["responsibility"]}\n"
    return doc

def generate_file_index():
    doc = """# FILE_INDEX.md

## 1. File-Level Class and Method Summary

This index provides an overview of each Python file, detailing the classes and their respective methods, along with a summary of their responsibilities and risk profiles.

"""
    for filepath in sorted(code_intelligence.keys()):
        doc += f"\n## File: `{filepath}`\n\n"
        classes = code_intelligence[filepath]
        if not classes:
            doc += "_No classes found in this file._\n\n"
        for class_name, methods in sorted(classes.items()):
            doc += f"### Class: `{class_name}`\n\n"
            if not methods:
                doc += "_No methods found in this class._\n\n"
            for method_name, method_details in sorted(methods.items()):
                summary = method_details["responsibility"].split("\n")[0]
                risk = method_details["risk_profile"]
                doc += f"*   `{method_name}`: {summary} (Risk: {risk})\n"
    return doc

def generate_module_deep_dives():
    doc = """# MODULE_DEEP_DIVES.md

## 1. Module-Level Deep Dives and Control Flow

This section provides in-depth explanations of key modules, emphasizing method-level control flow and interactions. Complex multi-class logic is visualized using Mermaid.js sequence diagrams or state diagrams.

"""
    # This will require more sophisticated analysis later to group by module and draw diagrams
    doc += "_Content for module deep dives will be generated here, including Mermaid.js diagrams for complex interactions._\n"
    
    # Breaking down the large string to avoid issues
    doc += "\n### Module: `nexus.sync.llm`\n\n"
    doc += "#### Class: `LLMRouter`\n\n"
    doc += "**Method: `route(req: LLMRequest) -> LLMRoute`**\n\n"
    doc += "*   **Control Flow**: This method acts as a deterministic dispatcher for LLM requests. It evaluates an `LLMRequest` object against a canonical routing table.\n"
    doc += "    1.  **Test Intent**: If `req.intent_class` is `TEST`, it immediately routes to `L0` (Mock provider).\n"
    doc += "    2.  **Cost Tolerance - Zero**: If `req.cost_tolerance` is `zero`, it attempts to route to a local LLM (`L1`, Ollama). If local LLMs are disabled, it raises an `LLMRoutingError`.\n"
    doc += "    3.  **Cost Tolerance - Low**: If `req.cost_tolerance` is `low`, it first attempts local LLM (`L1`). If local is not enabled, it falls back to a cheaper API model (`L2`, e.g., `gpt-4o-mini`), provided an API key is available. If neither is available, it raises `LLMRoutingError`.\n"
    doc += "    4.  **Cost Tolerance - High**: If `req.cost_tolerance` is `high`, it routes to a high-tier API model (`L3`, e.g., `gpt-4o`), strictly requiring an API key.\n"
    doc += "    5.  **Unhandled Cases**: Any unhandled request raises an `LLMRoutingError`.\n"
    doc += "*   **Interactions**: \n"
    doc += "    *   `LLMClient.generate` (caller)\n\n"
    doc += "#### Class: `LLMClient`\n\n"
    doc += "**Method: `generate(system_prompt, user_prompt, ...)`**\n\n"
    doc += "*   **Control Flow**: This method orchestrates the LLM call, including routing and executing the appropriate provider.\n"
    doc += "    1.  **Input Validation**: Raises `RuntimeError` if `intent_class` is `INGEST_EXTRACT` (mandating `StructuredIngestLLM`).\n"
    doc += "    2.  **Request Creation**: Constructs an `LLMRequest` object.\n"
    doc += "    3.  **Routing**: Calls `self.router.route(request)` to determine the LLM execution path.\n"
    doc += "    4.  **Error Handling**: Catches `LLMRoutingError`. In strict mode, it re-raises. Otherwise, it logs a critical error and falls back to `_mock_response`.\n"
    doc += "    5.  **Provider Execution**: \n"
    doc += "        *   If `mock`, calls `_mock_response`.\n"
    doc += "        *   If `ollama`, calls `_call_ollama`.\n"
    doc += "        *   If `api`, currently calls `_mock_response` (TODO: Implement actual API call).\n"
    doc += "*   **Interactions**: \n"
    doc += "    *   Calls `LLMRouter.route`.\n"
    doc += "    *   Calls `_mock_response` (internal).\n"
    doc += "    *   Calls `_call_ollama` (internal).\n"
    
    return doc

def generate_rules_and_invariants():
    doc = """# RULES_AND_INVARIANTS.md

## 1. Data & State Modeling

### 1.1. Core Entities (Nodes in Knowledge Graph)

*   **Intent**: Represents a core requirement, decision, or piece of knowledge. Has a `lifecycle` (LOOSE, FORMING, FROZEN, SUPERSEDED, KILLED) and `intent_type`.
    *   **State Transition**: LOOSE -> FORMING -> FROZEN -> SUPERSEDED / KILLED.
    *   **Transitions**: Managed by `GraphManager.promote_intent`.
*   **Source**: Raw input content from which intents or other nodes are extracted (e.g., code snippets, markdown sections).
*   **ScopeNode**: Defines the applicability or context of an Intent (e.g., "Frontend UI", "Database Layer").
*   **Brick**: A granular piece of information, potentially a precursor to an Intent or a structural element identified during ingestion.

### 1.2. Relationships (Edges in Knowledge Graph)

*   **DEPENDS_ON**: One intent/node relies on another.
*   **CONFLICTS_WITH**: Two intents/nodes are mutually exclusive or contradictory.
*   **OVERRIDES**: A newer or more specific intent/node replaces an older/general one. Crucially, the source must be `FROZEN`, and a target can only have one `OVERRIDES` edge. This ensures a clear lineage and prevents ambiguity.
*   **SUPERSEDED_BY**: Indicates an older node has been replaced by a newer one. Both must be `FROZEN` at the time of superseding.
*   **ASSEMBLED_IN**: Links a node (e.g., Brick, Intent) to a `Topic` (e.g., `nexus-server-sync`).
*   **APPLIES_TO**: Links an `Intent` to a `ScopeNode`, defining its architectural applicability.

## 2. State Transition Logic (Example: `IntentLifecycle`)

```mermaid
stateDiagram-v2
    [*] --> LOOSE
    LOOSE --> FORMING: promote_intent
    LOOSE --> KILLED: kill_node / promote_intent
    FORMING --> FROZEN: promote_node_to_frozen / promote_intent
    FORMING --> KILLED: kill_node / promote_intent
    FROZEN --> SUPERSEDED: supersede_node
    FROZEN --> KILLED: kill_node / promote_intent
    SUPERSEDED --> KILLED: kill_node / promote_intent
    KILLED --> [*]
```

*   **LOOSE**: Initial state, raw or unverified. Can be promoted to `FORMING` or `KILLED`.
*   **FORMING**: Under active review or refinement. Can be promoted to `FROZEN` or `KILLED`.
*   **FROZEN**: Stable, verified, and active. Can be `SUPERSEDED` or `KILLED`. Requires an `APPLIES_TO` edge.
*   **SUPERSEDED**: Replaced by a newer `FROZEN` intent. Can be `KILLED`.  
*   **KILLED**: Explicitly rejected or deprecated. Terminal state.

## 3. Entry Point Mapping

### 3.1. CLI Entry Points

*   **`src/nexus/cli/main.py`**:
    *   **`main()`**: The primary entry point for CLI operations, likely parsing arguments to dispatch commands.

### 3.2. API Entry Points

*   **`services/cortex/api.py`**:
    *   Contains FastAPI routes for exposing core Nexus functionalities.
    *   **Examples**: `/intents`, `/graphs`, `/query` (inferred).
*   **`services/cortex/server.py`**:
    *   Sets up the FastAPI application and serves the API.

### 3.3. Event Entry Points

*   **`services/cortex/tasks.py`**:
    *   Defines Celery tasks that can be triggered by events (e.g., new code commit, scheduled sync, user action).
    *   **Examples**: `process_ingestion_task`, `synthesize_relationships_task` (inferred).
*   **`src/nexus/sync/__main__.py`**:
    *   Likely an entry point for kick-starting the synchronization pipeline, possibly triggered by a cron job or a file system event listener.

## 4. Agent Safety Rails / Invariant Enforcers

This section explicitly lists critical invariants and \\\\\\\\\'Do Not Touch\\\\\\\\\' zones for agentic operations.

*   **Cycle Prevention (GraphManager)**: The `GraphManager._check_for_cycle` method explicitly prevents cycles when adding `OVERRIDES` or `SUPERSEDED_BY` edges. Any agent attempting to create a cyclical dependency of these types **MUST** be rejected.
    *   **Location**: `src/nexus/graph/manager.py`
    *   **Mandatory Verification Hook**: Agents proposing graph modifications MUST call `GraphManager.register_edge` and handle `ValueError` for cycle detection.

*   **LLM Routing Monotonicity (LLMRouter)**: The `LLMRouter` (`src/nexus/sync/llm.py`) implements a canonical, frozen routing table for LLM calls based on `intent_class` and `cost_tolerance`. Agents **MUST NOT** bypass this router or attempt to dynamically modify its logic.
    *   **Location**: `src/nexus/sync/llm.py` (`LLMRouter.route` method)
    *   **Mandatory Verification Hook**: All LLM calls involving external models **MUST** go through `LLMClient.generate` which, in turn, uses `LLMRouter.route`.

*   **Intent Lifecycle Monotonicity (GraphManager)**: Intents can only transition through predefined lifecycle states (`LOOSE` -> `FORMING` -> `FROZEN` -> `SUPERSEDED` / `KILLED`). Agents **MUST NOT** attempt to force invalid state transitions.
    *   **Location**: `src/nexus/graph/manager.py` (`GraphManager.promote_intent` method)
    *   **Mandatory Verification Hook**: Any agent modifying an `Intent` lifecycle **MUST** use `GraphManager.promote_intent` and respect the `ValueError` for invalid transitions.

*   **`FROZEN` Intent Invariants (GraphManager)**: An `Intent` cannot be `FROZEN` without an `APPLIES_TO` edge connecting it to a `ScopeNode`. This ensures all \\\\\\\\\'active\\\\\\\\\' intents have a defined architectural applicability.
    *   **Location**: `src/nexus/graph/manager.py` (`GraphManager.promote_intent` method)
    *   **Mandatory Verification Hook**: Agents proposing to `FREEZE` an `Intent` **MUST** ensure an `APPLIES_TO` edge exists or create one beforehand.

*   **Single `OVERRIDES` Target Invariant (GraphManager)**: A target node can only be `OVERRIDDEN` by a single source node. This prevents ambiguous overrides.
    *   **Location**: `src/nexus/graph/manager.py` (`GraphManager.add_typed_edge` method, for `EdgeType.OVERRIDES`)
    *   **Mandatory Verification Hook**: Agents attempting to create `OVERRIDES` edges **MUST** handle `ValueError` if the target is already overridden.

*   **Strict Structured Ingestion (StructuredIngestLLM)**: For critical ingestion tasks (`INGEST_EXTRACT` intent), agents **MUST** use `StructuredIngestLLM` to ensure deterministic, grammar-constrained output. Direct use of `LLMClient.generate` for this intent is forbidden.
    *   **Location**: `src/nexus/sync/llm.py` (`LLMClient.generate` and `StructuredIngestLLM`)
    *   **Mandatory Verification Hook**: Agents performing ingestion of structured data **MUST** utilize `StructuredIngestLLM.extract`.

*   **Economic Cognition Invariant (GraphManager)**: Any operation that invokes a non-free LLM model (`ModelTier.L2`, `L3`) **MUST** emit explicit cost metadata in the audit log.
    *   **Location**: `src/nexus/graph/manager.py` (`GraphManager._log_audit_event`)
    *   **Mandatory Verification Hook**: When logging audit events for paid LLM calls, agents **MUST** populate `cost_usd`, `tokens_in`, and `tokens_out` parameters.

---

"""
    return doc

def generate_gaps_and_todos():
    doc = """# GAPS_AND_TODOS.md

## 1. Identified Gaps and TODOs

This document highlights areas of missing information, incomplete implementations, and explicit TODOs found within the codebase and documentation analysis.

"""
    doc += "### 1.1. Missing/Uncertain Information from Context\n\n"
    for filepath, classes in code_intelligence.items():
        for class_name, methods in classes.items():
            for method_name, details in methods.items():
                if details["responsibility"] == "🔴 MISSING_FROM_CONTEXT":
                    doc += f"*   `{filepath}::{class_name}.{method_name}`: Responsibility is missing from docstring.\n"
                if details["inputs_outputs"] == "🔴 MISSING_FROM_CONTEXT":
                    doc += f"*   `{filepath}::{class_name}.{method_name}`: Inputs/Outputs description is missing from docstring.\n"
                if "🔴 MISSING_FROM_CONTEXT" in details["validation_invariants"]:
                    doc += f"*   `{filepath}::{class_name}.{method_name}`: Explicit validation/invariants not clearly identified.\n"

    doc += "\n### 1.2. Explicit TODOs in Code\n\n"
    # This part requires searching the raw files for \\\\\\\\\'TODO\\\\\\\\\' comments. 
    # For now, I\\\\\\\\\\'ll add a placeholder.
    doc += "_Scanning for explicit \\\\\\\\\'TODO\\\\\\\\\' comments in the codebase will be performed here._\n"
    doc += "\n*   `src/nexus/sync/llm.py` (LLMClient.generate): Implement actual API call for \\\\\\\\\'api\\\\\\\\\' provider."

    doc += "\n### 1.3. Implied Methods and Behaviors (🧪 or 🔴 Status)\n\n"
    # This will be populated during the deep dive analysis
    doc += "_Implied methods and behaviors described but not present in the code will be listed here._\n"
    return doc

def generate_inferred_enhancements():
    doc = """# INFERRED_ENHANCEMENTS.md

## 1. Inferred Enhancements and Refactoring Opportunities

This document outlines potential enhancements, refactoring opportunities, and architectural improvements inferred from the codebase analysis.

"""
    doc += "### 1.1. Potential Refactoring\n\n"
    doc += "*   **Centralized Error Handling/Logging**: While `GraphManager` has audit logging, a more centralized, standardized error handling and logging mechanism across all modules could improve observability and debuggability."
    doc += "*   **Asynchronous Operations**: Many LLM calls and potentially graph operations are I/O bound. Converting more operations to be truly asynchronous (e.g., using `async/await` throughout `LLMClient` and graph interactions) could improve performance and responsiveness."
    doc += "*   **Strict Schema Enforcement**: The `GraphManager` uses `json.dumps` and `json.loads` on node/edge data, which is flexible but less type-safe. More rigorous Pydantic models or similar for all data stored in the graph could prevent data corruption and improve consistency."

    doc += "\n### 1.2. New Feature Ideas / Architectural Improvements\n\n"
    doc += "*   **Dynamic LLM Routing Configuration**: The `LLMRouter` is currently \\\\\\\\\'FROZEN\\\\\\\\\". Introducing a mechanism for dynamic (but audited) updates to the routing table (e.g., via configuration files or an admin API) could allow for more flexible LLM management without code changes."
    doc += "*   **Graph Visualization Tooling**: Enhanced integration with UI components (like `ui/jarvis/`) to visualize the knowledge graph and its evolution in real-time, aiding in debugging and understanding agent behavior."
    doc += "*   **Advanced Invariant Checking**: Implement more sophisticated static analysis or runtime monitors to automatically detect violations of critical invariants (e.g., cyclical dependencies, lifecycle breaches) beyond basic checks."

    return doc

def generate_appendix():
    doc = """# APPENDIX.md

## 1. Consolidated Class -> Method -> Responsibility -> Risk -> Used By Reference Table

This table provides a comprehensive reference of all classes and their methods, including their responsibilities, risk profiles, and a summary of where they are called from.

"""
    doc += "| Class | Method Name | Responsibility | Risk Profile | Used By | Layer | Type |\n"
    doc += "|---|---|---|---|---|---|---|\n"

    all_classes_methods = get_all_classes_and_methods()
    reverse_calls = defaultdict(lambda: defaultdict(list))

    # First pass to build reverse call graph
    for filepath, classes in code_intelligence.items():
        for class_name, methods in classes.items():
            for method_name, details in methods.items():
                for called_method in details["calls"]:
                    # Heuristic: if a method `x` calls `y`, then `x` uses `y`.
                    # This doesn\\\\\\\\\\'t distinguish between `self.y()` and `other_obj.y()` yet.
                    reverse_calls[called_method][class_name].append(method_name)

    for class_path, class_info in sorted(all_classes_methods.items()):
        class_name = class_info["class_name"]
        for method_name, method_details in sorted(class_info["methods"].items()):
            responsibility = method_details["responsibility"].replace("\n", " ")[:100] + "..." if len(method_details["responsibility"]) > 100 else method_details["responsibility"].replace("\n", " ")
            risk = method_details["risk_profile"]

            used_by_entries = []
            for caller_class, caller_methods in reverse_calls[method_name].items():
                used_by_entries.append(f"{caller_class}.[{{', '.join(caller_methods)}}]")
            used_by = "; ".join(used_by_entries) if used_by_entries else "None"

            # Placeholder for Layer and Type
            layer = "🔴 MISSING_FROM_CONTEXT"
            method_type = "🔴 MISSING_FROM_CONTEXT"

            doc += f"| `{class_name}` | `{method_name}` | {responsibility} | {risk} | {used_by} | {layer} | {method_type} |\n"

    return doc

def main():
    global code_intelligence
    
    # Load the extracted code intelligence
    if os.path.exists("code_intelligence.json"):
        with open("code_intelligence.json", "r", encoding="utf-8") as f:
            code_intelligence = json.load(f)
    else:
        print("Error: code_intelligence.json not found. Please run generate_code_intelligence.py first.")
        return

    # Generate documents in specified order
    documents = [
        ("CANONICAL_OVERVIEW.md", generate_canonical_overview),
        ("IMPLEMENTATION_REALITY_MAP.md", generate_implementation_reality_map),
        ("FILE_INDEX.md", generate_file_index),
        ("MODULE_DEEP_DIVES.md", generate_module_deep_dives),
        ("RULES_AND_INVARIANTS.md", generate_rules_and_invariants),
        ("GAPS_AND_TODOS.md", generate_gaps_and_todos),
        ("INFERRED_ENHANCEMENTS.md", generate_inferred_enhancements),
        ("APPENDIX.md", generate_appendix),
    ]

    for filename, generator_func in documents:
        print(f"Generating {filename}...")
        content = generator_func()
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Successfully generated {filename}")

if __name__ == "__main__":
    main()
