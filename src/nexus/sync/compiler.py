import json
import hashlib
import os
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone

# For JSONPath, we might need a library like jsonpath-ng.
try:
    from jsonpath_ng import parse
except ImportError:
    parse = None

from nexus.sync.db import SyncDatabase

class NexusCompiler:
    def __init__(self, db_connection: SyncDatabase, llm_client: Any = None):
        self.db = db_connection
        self.llm_client = llm_client # Should be an interface with a .generate(prompt) method

    def compile_run(self, run_id: str, topic_id: str) -> int:
        """
        Main entry point for the compiler.
        Transforms raw run data into bricks for a specific topic.
        Returns the number of new bricks created.
        """
        # 1. Fetch Resources
        run = self.db.get_run(run_id)
        if not run:
            print(f"[Compiler] Run {run_id} not found.")
            return 0
        
        topic = self.db.get_topic(topic_id)
        if not topic:
            print(f"[Compiler] Topic {topic_id} not found.")
            return 0
        
        print(f"[Compiler] Compiling Run: {run_id} for Topic: {topic['display_name']}")

        # 2. Phase 1: Structural Scan (Optimization)
        scanned_nodes = self._pre_filter_nodes(run['raw_content'], topic['definition'])
        
        # 3. Phase 2: The Pointer Call (LLM)
        pointers = self._llm_extract_pointers(scanned_nodes, topic)
        
        # 4. Phase 3: The Mechanical Validator & Materialization
        new_bricks = []
        for ptr in pointers:
            brick = self._materialize_brick(run['raw_content'], run_id, ptr, topic_id)
            if brick:
                # 5. Commit to Vault
                self.db.save_brick(brick)
                new_bricks.append(brick)
                
        return len(new_bricks)

    def _pre_filter_nodes(self, raw_content: Any, definition: Dict) -> Any:
        """
        Filters the raw content to reduce context window usage.
        """
        if isinstance(raw_content, dict) and "messages" in raw_content:
            return raw_content["messages"]
        return raw_content

    def _llm_extract_pointers(self, content: Any, topic: Dict) -> List[Dict]:
        """
        Generates the Prompt and calls the LLM to get JSON pointers.
        """
        system_prompt = f"""You are a Deterministic Data Extraction Engine.
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
            try:
                response = self.llm_client.generate(system_prompt, user_prompt)
                cleaned_response = self._clean_llm_response(response)
                data = json.loads(cleaned_response)
                return data.get("extracted_pointers", [])
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

    def _materialize_brick(self, run_data: Any, run_id: str, pointer: Dict, topic_id: str) -> Optional[Dict]:
        """
        The Zero-Trust Validation Gate.
        """
        try:
            node_text = self._resolve_json_path(run_data, pointer['json_path'])
            if not isinstance(node_text, str):
                 node_text = str(node_text)
        except Exception as e:
            # print(f"❌ Path Error: {pointer['json_path']} - {e}")
            return None

        start_idx = node_text.find(pointer['verbatim_quote'])
        
        if start_idx == -1:
            # print(f"❌ Hallucination Detected: Quote not found in {pointer['json_path']}")
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
        Robust JSONPath resolver with support for content_blocks.
        """
        if parse:
             try:
                 jsonpath_expr = parse(path_str)
                 matches = [match.value for match in jsonpath_expr.find(data)]
                 if matches:
                     return matches[0]
             except Exception:
                 pass # Fallback to manual
        
        # Fallback manual parsing: $.messages[0].content_blocks[1].value
        parts = path_str.replace("$", "").strip(".").split(".")
        current = data
        try:
            for part in parts:
                if not part: continue
                if "[" in part and "]" in part:
                    key_part = part.split("[")[0]
                    idx_part = part.split("[")[1].split("]")[0]
                    if key_part:
                        current = current[key_part]
                    current = current[int(idx_part)]
                else:
                    current = current[part]
            return current
        except (KeyError, IndexError, ValueError, TypeError) as e:
            raise ValueError(f"Path resolution failed for {path_str}: {e}")
