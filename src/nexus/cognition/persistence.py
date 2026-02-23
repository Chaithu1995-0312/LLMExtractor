import json
import hashlib
from typing import Optional, Literal, Dict, Any
from datetime import datetime, timezone
from nexus.db import get_adapter

class CognitionLogger:
    """
    Handles persistence of L2/L3 cognitive outputs to the graph.cognition_logs table.
    Enforces append-only logging for auditability.
    """
    
    def __init__(self):
        self.db = get_adapter()

    def log_insight(
        self,
        layer: Literal["L2", "L3"],
        prompt: str,
        output: str,
        model: str,
        input_snapshot_hash: str,
        topic_id: Optional[str] = None,
        cluster_id: Optional[str] = None,
        trigger_event: Optional[str] = None,
        confidence_score: Optional[float] = None,
        latency_ms: Optional[int] = None,
        token_usage: Optional[int] = None,
        confidence_components: Optional[Dict[str, float]] = None,
        threshold_used: Optional[float] = None,
        escalation_tier: Optional[int] = None,
        budget_pressure: Optional[float] = None
    ) -> str:
        """
        Persists a cognitive insight with full V2 observability metadata.
        Returns the ID of the new log entry.
        """
        
        if layer not in ["L2", "L3"]:
            raise ValueError(f"Invalid layer: {layer}. Must be L2 or L3.")
            
        if confidence_score is not None:
             confidence_score = max(0.0, min(1.0, confidence_score))

        # Wrap in transaction to ensure consistency between log and calibration tables
        with self.db.transaction() as cur:
            cur.execute(
                """
                INSERT INTO graph.cognition_logs (
                    layer, topic_id, cluster_id, trigger_event,
                    input_snapshot_hash, prompt_text, output_text,
                    model_used, confidence_score, latency_ms, token_usage,
                    confidence_components, threshold_used, escalation_tier, budget_pressure,
                    created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                RETURNING id
                """,
                (
                    layer, topic_id, cluster_id, trigger_event,
                    input_snapshot_hash, prompt, output,
                    model, confidence_score, latency_ms, token_usage,
                    json.dumps(confidence_components) if confidence_components else None,
                    threshold_used, escalation_tier, budget_pressure
                )
            )
            log_id = cur.fetchone()[0]
            
            # 2. Log to Calibration Table (Immediate predicted confidence snapshot)
            if confidence_score is not None:
                 cur.execute(
                     """
                     INSERT INTO graph.cognition_calibration (log_id, predicted_confidence, created_at)
                     VALUES (%s, %s, NOW())
                     """,
                     (log_id, confidence_score)
                 )
        
        print(f"[CognitionLogger] Logged {layer} insight (ID: {log_id}) for event: {trigger_event}")
        return str(log_id)

    def generate_snapshot_hash(self, data: Any) -> str:
        """
        Generates a stable hash for the input data snapshot.
        If data is a complex object, it should be JSON-serializable.
        """
        if isinstance(data, str):
            content = data.encode("utf-8")
        else:
            # Sort keys for deterministic hashing
            content = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
            
        return hashlib.sha256(content).hexdigest()
