import json
import hashlib
import os
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timezone
from nexus.graph.schema import AuditEventType, ModelTier, DecisionAction
from nexus.bricks.resolver import UserTriggeredResolver

# For JSONPath, we might need a library like jsonpath-ng.
try:
    from jsonpath_ng import parse
except ImportError:
    parse = None

from nexus.sync.db import SyncDatabase
from nexus.graph.prompt_manager import PromptManager
from nexus.cognition.coverage_sentinel import CoverageSentinel
from nexus.governance.alert_manager import AlertManager

# INGESTION PIPELINE — FROZEN
# Changes here require epistemic review

# Performance and Determinism Constants
MAX_MESSAGES_PER_BATCH = 5
MAX_CHARS_PER_BATCH = 8000
MAX_SINGLE_MESSAGE_CHARS = 2000

SIGNAL_TOKENS = [
    "must", "should", "cannot", "never",
    "rule", "constraint", "invariant",
    "architecture", "design",
    "pipeline", "sync", "boundary",
    "fails", "guarantee", "ensures",
    "requires", "only if"
]

class NexusCompiler:
    def __init__(self, db_connection: SyncDatabase, llm_client: Any = None):
        self.db = db_connection
        self.llm_client = llm_client # Should be an interface with a .generate(prompt) method
        self.prompt_manager = PromptManager()
        self.coverage_sentinel = CoverageSentinel(llm_client) if llm_client else None
        self.alert_manager = AlertManager()

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

        # 2. Phase 1: Structural Scan & Prefilter (Lexer)
        filtered_messages, max_index = self._pre_filter_nodes(run['raw_content'], last_processed)
        
        if not filtered_messages:
            print(f"[Compiler] No signal detected in new content for Run {run_id}")
            # Even if no signal, we advance the boundary to avoid re-scanning known junk
            if max_index > last_processed:
                self.db.update_run_boundary(run_id, max_index)
            
            graph_manager._log_audit_event(
                event_type=AuditEventType.LLM_CALL_SKIPPED,
                agent="NexusCompiler",
                component="compiler",
                decision_action=DecisionAction.SKIPPED,
                reason="No signal detected in messages beyond last_processed_index",
                run_id=run_id,
                topic_id=topic_id
            )
            return 0

        # 3. Phase 2: Bounded Batching (Parser)
        batches = self._build_batches(filtered_messages)
        print(f"[Compiler] Split {len(filtered_messages)} messages into {len(batches)} batches.")

        all_pointers = []
        for i, batch in enumerate(batches):
            print(f"[Compiler] Processing batch {i+1}/{len(batches)} ({len(batch)} nodes)...")
            # Inject batch context if needed (can be added to _llm_extract_pointers)
            batch_pointers = self._llm_extract_pointers(batch, topic)
            all_pointers.extend(batch_pointers)
        
        # Track scanned indices for path boundary enforcement
        # We use a set of all indices that WERE scanned (including filtered ones)
        scanned_indices = set(range(last_processed + 1, max_index + 1))

        # 4. Phase 3: The Mechanical Validator & Materialization (Type Checker)
        new_bricks = []
        for ptr in all_pointers:
            brick = self._materialize_brick(run['raw_content'], run_id, ptr, topic_id, scanned_indices)
            if brick:
                # 5. Commit to Vault
                self.db.save_brick(brick)
                new_bricks.append(brick)
        
        # 6. Transactional Boundary Update
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

        # 7. Coverage Sentinel Analysis (Local Intelligence)
        if self.coverage_sentinel and new_bricks:
            try:
                # Fetch existing intents for context
                intents = graph_manager.get_intents_by_topic(f"topic_{topic_id}")
                intent_dicts = []
                for i in intents:
                    intent_dicts.append({
                        "id": i.id,
                        "statement": i.statement,
                        "lifecycle": i.lifecycle.value
                    })
                
                alerts = self.coverage_sentinel.analyze_topic(topic['display_name'], new_bricks, intent_dicts)
                
                for alert in alerts:
                    if alert.get("is_duplicate"):
                        # Skip Pulse, Log Duplicate
                        graph_manager._log_audit_event(
                            event_type=AuditEventType.COVERAGE_ALERT_SKIPPED_DUPLICATE,
                            agent="CoverageSentinel",
                            component="cognition",
                            decision_action=DecisionAction.SKIPPED,
                            reason=f"Duplicate alert suppressed: {alert.get('details', {}).get('summary', 'Unknown')}",
                            topic_id=topic_id,
                            metadata={
                                "alert_id": alert.get("alert_id"),
                                "suppressed_fingerprint": alert.get("fingerprint")
                            }
                        )
                        continue

                    # Emit Pulse
                    graph_manager._emit_pulse(
                        event_type=alert.get("type", "COVERAGE_ALERT"),
                        payload=alert.get("details", {}),
                        topic_id=topic_id,
                        severity=alert.get("severity", "info"),
                        source="CoverageSentinel"
                    )
                    
                    # Persist Alert (New Governance Layer)
                    self.alert_manager.persist_alert(alert)

                    # Log Audit
                    graph_manager._log_audit_event(
                        event_type=AuditEventType.COVERAGE_ALERT_EMITTED,
                        agent="CoverageSentinel",
                        component="cognition",
                        decision_action=DecisionAction.ACCEPTED,
                        reason=alert.get("details", {}).get("summary", "Coverage Alert"),
                        topic_id=topic_id,
                        metadata=alert
                    )
            except Exception as e:
                print(f"[Compiler] Coverage Sentinel Error: {e}")
                
        return len(new_bricks)

    def _reject_message(self, msg: Dict) -> bool:
        """Cheap structural rejection logic."""
        content = msg.get("content", "")
        if not content:
            return True
        if msg.get("role") == "assistant" and "Hallucination Artifact" in content:
            return True
        if msg.get("role") == "system" and not content.strip():
            return True
        return False

    def _has_signal(self, text: str) -> bool:
        """Lexical signal gate."""
        t = text.lower()
        return any(tok in t for tok in SIGNAL_TOKENS)

    def _pre_filter_nodes(self, raw_content: Any, last_processed: int = -1) -> Tuple[List[Dict], int]:
        """
        Filters the raw content to reduce context window usage.
        Implements both Incremental Boundary Guard and Content-based filtering.
        Returns (filtered_messages, max_index_seen).
        """
        # INGESTION PIPELINE — FROZEN
        if isinstance(raw_content, dict) and "messages" in raw_content:
            messages = raw_content["messages"]
            filtered_messages = []
            max_idx = last_processed
            skipped_non_authoritative = 0
            
            for i, msg in enumerate(messages):
                if i <= last_processed:
                    continue
                
                max_idx = i

                # 🔒 Ingestion authority rule (final)
                # Only user and system roles are authoritative.
                # assistant -> derivative cognition ❌
                # tool -> execution/meta artifacts ❌
                if msg.get("role") not in ("user", "system"):
                    skipped_non_authoritative += 1
                    continue
                
                # 1. Structural Rejection
                if self._reject_message(msg):
                    continue
                
                # 2. Signal Gate
                if not self._has_signal(msg.get("content", "")):
                    continue
                    
                # Store original index for path reconstruction
                msg_with_meta = msg.copy()
                msg_with_meta["_original_index"] = i
                filtered_messages.append(msg_with_meta)
            
            if skipped_non_authoritative > 0:
                print(f"[Compiler] Skipped {skipped_non_authoritative} non-authoritative messages by ingestion policy.")
                
            return filtered_messages, max_idx
            
        return [], last_processed

    def _build_batches(self, messages: List[Dict]) -> List[List[Dict]]:
        """Bounded batch construction algorithm."""
        # INGESTION PIPELINE — FROZEN
        batches = []
        current_batch = []
        current_chars = 0

        for msg in messages:
            # We copy to avoid modifying original msg if we truncate
            msg_copy = msg.copy()
            
            # Optional: Truncate extremely large single messages before calculating size
            if "content" in msg_copy and isinstance(msg_copy["content"], str) and len(msg_copy["content"]) > MAX_SINGLE_MESSAGE_CHARS:
                msg_copy["content"] = msg_copy["content"][:MAX_SINGLE_MESSAGE_CHARS] + "... [truncated]"

            text = json.dumps(msg_copy)
            size = len(text)
            
            # print(f"DEBUG: Processing msg, size={size}, current_chars={current_chars}")

            # Flush batch if adding would exceed limits
            if current_batch:
                if len(current_batch) >= MAX_MESSAGES_PER_BATCH or current_chars + size > MAX_CHARS_PER_BATCH:
                    # print(f"DEBUG: Flushing batch. len={len(current_batch)}, chars={current_chars}")
                    batches.append(current_batch)
                    current_batch = []
                    current_chars = 0

            current_batch.append(msg_copy)
            current_chars += size

        if current_batch:
            batches.append(current_batch)

        return batches

    def _llm_extract_pointers(self, content: Any, topic: Dict) -> List[Dict]:
        """
        Generates the Prompt and calls the LLM to get JSON pointers.
        """
        # INGESTION PIPELINE — FROZEN
        fallback_system = f"""You are a Deterministic Data Extraction Engine.
You are NOT a chat assistant. You are a compiler component.
Your task is mechanical, not creative.

GOAL
Scan the provided Source JSON and identify explicit technical statements, rules, 
constraints, or architectural decisions that match the target topic.

IMPORTANT
Most messages are irrelevant. 
If a message does not clearly contain a technical rule, constraint, architectural decision, 
or data-flow requirement, you MUST ignore it and return no pointers for that message.

CRITICAL RULES (VIOLATION = SYSTEM FAILURE)
1. NO PARAPHRASING. Copy text exactly as it appears in the source.
2. NO MERGING. One pointer per statement.
3. NO INFERENCE. If unsure, extract nothing.
4. IGNORE SPECULATION, analogies, or metaphors.
5. IGNORE CONTENT that does not directly affect system behavior.

OUTPUT
Return a JSON object:
{{
  "extracted_pointers": [
    {{
      "topic_id": "{topic['id']}",
      "json_path": "string (RFC 9535 standard path, e.g., $.messages[3].content)",
      "verbatim_quote": "string (exact copy-paste of the text)"
    }}
  ]
}}

If no valid statements exist, return:
{{ "extracted_pointers": [] }}
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

        # Deterministic lifecycle initialization
        # If it contains a question mark and is from assistant, it's LOOSE
        # But here we are materializing based on LLM pointers, so we need to check the source node
        state = "IMPROVISE"
        if "?" in pointer['verbatim_quote'] and "assistant" in pointer['json_path']:
             state = "LOOSE"

        return {
            "id": brick_id,
            "topic_id": topic_id,
            "content": pointer['verbatim_quote'],
            "fingerprint": fingerprint,
            "state": state,
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
