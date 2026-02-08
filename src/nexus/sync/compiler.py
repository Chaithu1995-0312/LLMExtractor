import json
import hashlib
import os
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timezone
from nexus.graph.schema import AuditEventType, ModelTier, DecisionAction

# For JSONPath, we might need a library like jsonpath-ng.
try:
    from jsonpath_ng import parse
except ImportError:
    parse = None

from nexus.sync.db import SyncDatabase
from nexus.graph.prompt_manager import PromptManager

class NexusCompiler:
    def __init__(self, db_connection: SyncDatabase, llm_client: Any = None):
        self.db = db_connection
        self.llm_client = llm_client # Should be an interface with a .generate(prompt) method
        self.prompt_manager = PromptManager()

    def compile_run(self, run_id: str, topic_id: str) -> int:
        """
        Main entry point for the compiler.
        Transforms raw run data into bricks for a specific topic.
        Returns the number of new bricks created.
        """
        from nexus.graph.manager import GraphManager
        graph_manager = GraphManager()
        self.graph_manager = graph_manager

        # 1. Fetch Resources
        run = self.db.get_run(run_id)
        if not run:
            print(f"[Compiler] Run {run_id} not found.")
            return 0
        
        topic = self.db.get_topic(topic_id)
        if not topic:
            print(f"[Compiler] Topic {topic_id} not found.")
            return 0
        
        last_processed = run.get('last_processed_index', -1)
        
        graph_manager._log_audit_event(
            event_type=AuditEventType.RUN_COMPILE_STARTED,
            agent="NexusCompiler",
            component="compiler",
            decision_action=DecisionAction.ACCEPTED,
            reason=f"Starting compilation for {topic['display_name']}",
            run_id=run_id,
            topic_id=topic_id,
            metadata={"last_processed_index": last_processed}
        )

        print(f"[Compiler] Compiling Run: {run_id} for Topic: {topic['display_name']} (from index {last_processed + 1})")

        # 2. Phase 1: Structural Scan (Optimization + Boundary Guard)
        scanned_nodes, max_index = self._pre_filter_nodes(run['raw_content'], topic['definition'], last_processed)
        
        if not scanned_nodes:
            print(f"[Compiler] No new content to process for Run {run_id}")
            graph_manager._log_audit_event(
                event_type=AuditEventType.LLM_CALL_SKIPPED,
                agent="NexusCompiler",
                component="compiler",
                decision_action=DecisionAction.SKIPPED,
                reason="No new messages beyond last_processed_index",
                run_id=run_id,
                topic_id=topic_id
            )
            return 0

        # 3. Phase 2: The Pointer Call (LLM)
        pointers = self._llm_extract_pointers(scanned_nodes, topic)
        
        # Track scanned indices for path boundary enforcement
        scanned_indices = set()
        if isinstance(run['raw_content'], dict) and "messages" in run['raw_content']:
            for i, _ in enumerate(run['raw_content']['messages']):
                if i > last_processed:
                    scanned_indices.add(i)

        # 4. Phase 3: The Mechanical Validator & Materialization
        new_bricks = []
        for ptr in pointers:
            brick = self._materialize_brick(run['raw_content'], run_id, ptr, topic_id, scanned_indices)
            if brick:
                # 5. Commit to Vault
                self.db.save_brick(brick)
                new_bricks.append(brick)
        
        # 6. Transactional Boundary Update
        # Only advance if we successfully reached this point (no crash in LLM or materialization)
        if max_index > last_processed:
            self.db.update_run_boundary(run_id, max_index)
            graph_manager._log_audit_event(
                event_type=AuditEventType.BOUNDARY_ADVANCED,
                agent="NexusCompiler",
                component="compiler",
                decision_action=DecisionAction.ACCEPTED,
                reason=f"Advanced boundary to {max_index}",
                run_id=run_id,
                topic_id=topic_id,
                metadata={"before": last_processed, "after": max_index}
            )
            
        graph_manager._log_audit_event(
            event_type=AuditEventType.RUN_COMPILE_COMPLETED,
            agent="NexusCompiler",
            component="compiler",
            decision_action=DecisionAction.ACCEPTED,
            reason=f"Completed. Created {len(new_bricks)} bricks.",
            run_id=run_id,
            topic_id=topic_id,
            metadata={"new_bricks": len(new_bricks)}
        )
                
        return len(new_bricks)

    def _pre_filter_nodes(self, raw_content: Any, definition: Dict, last_processed: int = -1) -> Tuple[Any, int]:
        """
        Filters the raw content to reduce context window usage.
        Implements the Incremental Boundary Guard.
        Returns (filtered_content, max_index_seen).
        """
        if isinstance(raw_content, dict) and "messages" in raw_content:
            messages = raw_content["messages"]
            new_messages = []
            max_idx = last_processed
            
            for i, msg in enumerate(messages):
                if i > last_processed:
                    new_messages.append(msg)
                    max_idx = max(max_idx, i)
            
            return new_messages, max_idx
            
        return raw_content, last_processed

    def _llm_extract_pointers(self, content: Any, topic: Dict) -> List[Dict]:
        """
        Generates the Prompt and calls the LLM to get JSON pointers.
        """
        fallback_system = f"""You are a Deterministic Data Extraction Engine.
You are NOT a chat assistant. You are a compiler component.

Your Goal: Scan the provided Source JSON and identify text segments that belong to the requested Topic IDs.
Your Output: A raw JSON array of "Pointer Objects."

---

### INPUT DATA
1. "Topics": A list of Topic IDs and their descriptions.
2. "Source_JSON": A raw JSON transcript. Nodes may contain:
   - "content": A plain-text fallback string.
   - "content_blocks": Structured blocks (text, code, tool_output). PREFER these for precise extraction.
   - "metadata": Contextual info (content_type, recipient, model).

---

### CRITICAL RULES (VIOLATION = SYSTEM FAILURE)
1. NO PARAPHRASING: You must return the text EXACTLY as it appears in the source.
2. NO MERGING: If information is split across nodes, output separate Pointer Objects.
3. PREFER STRUCTURE: If a fact is found in a `content_blocks` node (e.g., a code snippet or tool result), use the path to that specific block.
4. NO INTERPRETATION: Do not infer facts. Only extract explicit statements.

---

### OUTPUT SCHEMA
Return a JSON Object with a single key "extracted_pointers" containing a list:

{{
  "extracted_pointers": [
    {{
      "topic_id": "string (must match one of the Input Topics)",
      "json_path": "string (RFC 9535 standard path, e.g., $.messages[3].content_blocks[0].value)",
      "verbatim_quote": "string (exact copy-paste of the text found at that path)"
    }}
  ]
}}
"""
        system_prompt = self.prompt_manager.get_prompt("nexus-compiler-system", fallback=fallback_system)
        
        user_prompt = f"""
TARGET TOPIC: "{topic['id']}"

DEFINITION:
{topic['definition'].get('scope_description', '')}

EXCLUSIONS (Do NOT extract):
{json.dumps(topic['definition'].get('exclusion_criteria', []))}

SOURCE JSON TO SCAN:
{json.dumps(content, ensure_ascii=False)}
"""
        
        # Call LLM
        if self.llm_client:
            from nexus.graph.manager import GraphManager
            graph_manager = GraphManager()
            
            # Estimate tokens (approx 4 chars per token)
            tokens_in = (len(system_prompt) + len(user_prompt)) // 4
            
            try:
                response = self.llm_client.generate(system_prompt, user_prompt)
                tokens_out = len(response) // 4
                
                # Estimate cost for L2 ($0.01 per 1k total tokens)
                estimated_cost = ((tokens_in + tokens_out) / 1000.0) * 0.01

                graph_manager._log_audit_event(
                    event_type=AuditEventType.LLM_CALL_EXECUTED,
                    agent="NexusCompiler",
                    component="compiler",
                    decision_action=DecisionAction.LLM_CALL,
                    reason="Executing extraction LLM call",
                    topic_id=topic['id'],
                    model_tier=ModelTier.L2,
                    cost_usd=estimated_cost,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    metadata={"prompt_char_count": len(user_prompt)}
                )

                cleaned_response = self._clean_llm_response(response)
                data = json.loads(cleaned_response)
                pointers = data.get("extracted_pointers", [])
                
                graph_manager._log_audit_event(
                    event_type=AuditEventType.POINTERS_EXTRACTED,
                    agent="NexusCompiler",
                    component="compiler",
                    decision_action=DecisionAction.ACCEPTED,
                    reason=f"Extracted {len(pointers)} potential pointers",
                    topic_id=topic['id'],
                    metadata={"pointer_count": len(pointers)}
                )
                
                return pointers
            except Exception as e:
                print(f"[Compiler] LLM Call Failed: {e}")
                return []
        else:
            print("[Compiler] No LLM Client configured.")
            return []

    def _clean_llm_response(self, response: str) -> str:
        """Helper to extract JSON from LLM markdown."""
        if "```json" in response:
            return response.split("```json")[1].split("```")[0].strip()
        if "```" in response:
            return response.split("```")[1].split("```")[0].strip()
        return response.strip()

    def _materialize_brick(self, run_data: Any, run_id: str, pointer: Dict, topic_id: str, scanned_indices: set = None) -> Optional[Dict]:
        """
        The Zero-Trust Validation Gate.
        """
        from nexus.graph.schema import AuditEventType, DecisionAction

        # Trust Boundary 1: Topic ID Mismatch
        if pointer.get('topic_id') != topic_id:
            self.graph_manager._log_audit_event(
                event_type=AuditEventType.LLM_POINTER_MISMATCH,
                agent="NexusCompiler",
                component="compiler",
                decision_action=DecisionAction.REJECTED,
                reason=f"LLM suggested topic {pointer.get('topic_id')} but run is for {topic_id}",
                topic_id=topic_id,
                run_id=run_id,
                metadata={"pointer": pointer}
            )
            return None

        # Trust Boundary 2: JSON Path Out of Bounds (Incremental Guard)
        if scanned_indices is not None and "messages[" in pointer.get('json_path', ''):
            try:
                # Extract index from $.messages[N]...
                path = pointer['json_path']
                idx_str = path.split("messages[")[1].split("]")[0]
                idx = int(idx_str)
                if idx not in scanned_indices:
                     self.graph_manager._log_audit_event(
                        event_type=AuditEventType.LLM_PATH_OUT_OF_BOUNDS,
                        agent="NexusCompiler",
                        component="compiler",
                        decision_action=DecisionAction.REJECTED,
                        reason=f"LLM pointed to message {idx} which is outside the current scan window.",
                        topic_id=topic_id,
                        run_id=run_id,
                        metadata={"pointer": pointer, "scanned_indices": list(scanned_indices)}
                    )
                     return None
            except (IndexError, ValueError):
                pass # Path might not be a standard message path, allow resolve attempt

        try:
            node_text = self._resolve_json_path(run_data, pointer['json_path'])
            if not isinstance(node_text, str):
                 node_text = str(node_text)
        except Exception as e:
            # print(f"❌ Path Error: {pointer['json_path']} - {e}")
            return None

        # Hard Verification Gate: Verbatim quote must exist at path
        start_idx = node_text.find(pointer['verbatim_quote'])
        
        if start_idx == -1:
            # Audit Hallucination
            self.graph_manager._log_audit_event(
                event_type=AuditEventType.LLM_HALLUCINATION_DETECTED,
                agent="NexusCompiler",
                component="compiler",
                decision_action=DecisionAction.REJECTED,
                reason=f"Verbatim quote not found at path {pointer['json_path']}",
                topic_id=topic_id,
                run_id=run_id,
                metadata={"pointer": pointer}
            )
            return None # HARD REJECT

        end_idx = start_idx + len(pointer['verbatim_quote'])

        norm_text = pointer['verbatim_quote'].strip().lower()
        fingerprint = hashlib.sha256(norm_text.encode()).hexdigest()
        node_checksum = hashlib.sha256(node_text.encode()).hexdigest()
        brick_id = hashlib.sha256((topic_id + fingerprint).encode()).hexdigest()

        return {
            "id": brick_id,
            "topic_id": topic_id,
            "content": pointer['verbatim_quote'],
            "fingerprint": fingerprint,
            "state": "IMPROVISE",
            "source_address": {
                "run_id": run_id,
                "json_path": pointer['json_path'],
                "indices": [start_idx, end_idx],
                "checksum": node_checksum
            }
        }

    def _resolve_json_path(self, data: Any, path_str: str) -> Any:
        """
        Robust JSONPath resolver with support for content_blocks using jsonpath-ng.
        """
        if not parse:
             raise ImportError("jsonpath-ng is not installed.")

        try:
            jsonpath_expr = parse(path_str)
            matches = [match.value for match in jsonpath_expr.find(data)]
            if matches:
                return matches[0]
            raise ValueError(f"No matches found for path: {path_str}")
        except Exception as e:
            # Enhanced error logging for debugging
            print(f"[Compiler] JSONPath Error: {path_str} - {e}")
            raise ValueError(f"Path resolution failed for {path_str}: {e}")
