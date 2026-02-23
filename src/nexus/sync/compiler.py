import json
import hashlib
import os
import asyncio
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timezone
from nexus.graph.schema import AuditEventType, ModelTier, DecisionAction
from nexus.sync.db import SyncDatabase
from nexus.graph.prompt_manager import PromptManager
from nexus.governance.alert_manager import AlertManager

# INGESTION PIPELINE — DETERMINISTIC COMPILER v2
# Changes here require epistemic review

class NexusCompiler:
    def __init__(self, db_connection: SyncDatabase, llm_client: Any = None):
        self.db = db_connection
        # LLM client is explicitly banned from Level 0 Compiler
        self.llm_client = None 
        self.prompt_manager = PromptManager()
        # CoverageSentinel removed from Level 0 to maintain Zero-LLM purity
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

        # 2. Deterministic Message Materialization Loop
        raw_content = run['raw_content']
        new_bricks = []
        max_idx = last_processed

        if isinstance(raw_content, dict) and "messages" in raw_content:
            messages = raw_content["messages"]
            
            for i, msg in enumerate(messages):
                if i <= last_processed:
                    continue
                
                max_idx = i

                # 🔒 Ingestion authority rule (tiered authority model)
                role = msg.get("role")
                if role not in ("user", "system", "assistant"):
                    continue
                
                # Materialize Brick 1:1
                brick = self._materialize_message_brick(msg, i, run_id, topic_id)
                if brick:
                    # Commit to Vault Atomically (Level 0 Hardening)
                    # Subsumption is now handled inside this atomic call
                    self.db.save_brick_atomic(brick)
                    new_bricks.append(brick)
        
        # 3. Transactional Boundary Update
        if max_idx > last_processed:
            self.db.update_run_boundary(run_id, max_idx)
            graph_manager._log_audit_event(
                event_type=AuditEventType.BOUNDARY_ADVANCED,
                agent="NexusCompiler",
                component="compiler",
                decision_action=DecisionAction.ACCEPTED,
                reason=f"Advanced boundary to {max_idx}",
                run_id=run_id,
                topic_id=topic_id,
                metadata={"before": last_processed, "after": max_idx}
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

        # 4. Coverage Sentinel Analysis Removed from Level 0
        # It must be run as a post-processing task in Level 1 (Evolution Layer)
        # to maintain the Zero-LLM guarantee of the compiler.
                
        return len(new_bricks)

    def _materialize_message_brick(self, msg: Dict, idx: int, run_id: str, topic_id: str) -> Optional[Dict]:
        """
        Deterministic brick creation from a message (Level 0 Hardening).
        Enforces canonical normalization and pure function guarantees.
        """
        content = msg.get("content", "")
        if not content:
            return None

        # Handle complex content (e.g. lists of parts)
        if isinstance(content, list):
            # Deterministic join: enforce sorted keys if we ever serialize dicts,
            # but here we just join text parts in order.
            text_parts = []
            for part in content:
                if isinstance(part, str):
                    text_parts.append(part)
                elif isinstance(part, dict) and "text" in part:
                    text_parts.append(part["text"])
            content = "\n".join(text_parts)
        elif not isinstance(content, str):
            content = str(content)

        # 1. Canonical Normalization (Byte Stability)
        # We explicitly normalize newlines AND strip whitespace to ensure identity stability.
        # Stored content MUST match hashed content.
        canonical_content = content.replace("\r\n", "\n").strip()

        role = msg.get("role")
        
        authority_map = {
            "system": "ROOT",
            "user": "PRIMARY",
            "assistant": "DERIVED"
        }
        authority_level = authority_map.get(role, "PRIMARY")

        message_id = msg.get("id", f"msg_{idx}") # Fallback if ID is missing

        # Brick Identity: sha256(run_id + message_id)
        # This ensures 1:1 mapping and determinism across re-runs
        identity_string = f"{run_id}:{message_id}"
        brick_id = hashlib.sha256(identity_string.encode("utf-8")).hexdigest()

        # Fingerprint: sha256(canonical_content)
        # Content is already stripped. Hash must match exactly what is stored.
        fingerprint = hashlib.sha256(canonical_content.encode("utf-8")).hexdigest()
        
        # Checksum: sha256(canonical_content)
        # Strict byte-for-byte checksum of what is stored.
        node_checksum = hashlib.sha256(canonical_content.encode("utf-8")).hexdigest()
        
        initial_state = "IMPROVISE"
        
        return {
            "id": brick_id,
            "topic_id": topic_id,
            "content": canonical_content, # Stored content is stripped & normalized
            "fingerprint": fingerprint,
            "state": initial_state,
            "role": role,
            "authority_level": authority_level,
            "message_id": message_id,
            "source_address": {
                "run_id": run_id,
                "json_path": f"$.messages[{idx}]",
                "indices": [0, len(canonical_content)],
                "checksum": node_checksum
            }
        }
