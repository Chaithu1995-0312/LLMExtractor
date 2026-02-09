import json
import sqlite3
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from nexus.config import GRAPH_DB_PATH

class AlertManager:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or GRAPH_DB_PATH

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def persist_alert(self, alert_data: Dict[str, Any]):
        """
        Idempotent insert of a coverage alert.
        If fingerprint exists, we might update or ignore (schema says UNIQUE(fingerprint)).
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            # We assume alert_data matches the schema fields roughly
            # alert_id, fingerprint, topic_id, type, severity, signal_score, 
            # state, summary, created_at, updated_at, details (as json)
            
            ts = datetime.now(timezone.utc).isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO coverage_alerts (
                    alert_id, fingerprint, topic_id, type, severity, signal_score,
                    state, summary, created_at, updated_at, resolution_metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert_data['alert_id'],
                alert_data['fingerprint'],
                alert_data['topic_id'],
                alert_data['type'],
                alert_data['severity'],
                alert_data['signal_score'],
                "NEW", # Initial state
                alert_data['details'].get('summary', ''),
                alert_data.get('generated_at', ts),
                ts,
                json.dumps(alert_data.get('details', {}))
            ))
            conn.commit()
        except Exception as e:
            print(f"[AlertManager] Error persisting alert: {e}")
        finally:
            conn.close()

    def get_alerts_for_topic(self, topic_id: str) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM coverage_alerts WHERE topic_id = ?", (topic_id,))
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            results.append(dict(zip(columns, row)))
            
        conn.close()
        return results

    def acknowledge_alert(self, alert_id: str, actor: str) -> bool:
        return self._transition_state(alert_id, "ACKNOWLEDGED", actor)

    def dismiss_alert(self, alert_id: str, actor: str, reason: str) -> bool:
        return self._transition_state(alert_id, "DISMISSED", actor, dismissed_reason=reason)

    def resolve_alert(self, alert_id: str, actor: str, action: str, metadata: Dict) -> bool:
        return self._transition_state(alert_id, "RESOLVED", actor, 
                                      resolution_action=action, 
                                      resolution_metadata=metadata)

    def archive_alert(self, alert_id: str) -> bool:
        # Check current state first
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT state FROM coverage_alerts WHERE alert_id = ?", (alert_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return False
            
        current_state = row[0]
        if current_state not in ['RESOLVED', 'DISMISSED']:
            print(f"[AlertManager] Cannot archive alert {alert_id} from state {current_state}")
            return False

        # Transition
        conn = self._get_conn()
        try:
            ts = datetime.now(timezone.utc).isoformat()
            conn.execute("""
                UPDATE coverage_alerts 
                SET state = ?, updated_at = ?
                WHERE alert_id = ?
            """, ("ARCHIVED", ts, alert_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"[AlertManager] Error archiving: {e}")
            return False
        finally:
            conn.close()

    def log_prompt_attempt(self, attempt_data: Dict[str, Any]):
        """
        Log an auto-suggested prompt attempt.
        """
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO coverage_prompt_attempts (
                    id, alert_id, topic_id, prompt, attempted_at, outcome, bricks_created
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                attempt_data['id'],
                attempt_data['alert_id'],
                attempt_data['topic_id'],
                attempt_data['prompt'],
                attempt_data['attempted_at'],
                attempt_data.get('outcome', 'SUCCESS'),
                attempt_data.get('bricks_created', 0)
            ))
            conn.commit()
        except Exception as e:
            print(f"[AlertManager] Error logging prompt attempt: {e}")
        finally:
            conn.close()

    def get_recent_prompt_attempts(self, topic_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM coverage_prompt_attempts 
            WHERE topic_id = ? 
            ORDER BY attempted_at DESC 
            LIMIT ?
        """, (topic_id, limit))
        
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            results.append(dict(zip(columns, row)))
            
        conn.close()
        return results

    def get_alert(self, alert_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM coverage_alerts WHERE alert_id = ?", (alert_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            columns = [col[0] for col in cursor.description]
            return dict(zip(columns, row))
        return None

    def _transition_state(self, alert_id: str, new_state: str, actor: str, 
                          dismissed_reason: str = None, 
                          resolution_action: str = None,
                          resolution_metadata: Dict = None) -> bool:
        conn = self._get_conn()
        try:
            ts = datetime.now(timezone.utc).isoformat()
            
            updates = ["state = ?", "updated_at = ?"]
            params = [new_state, ts]
            
            if new_state == "ACKNOWLEDGED":
                updates.append("acknowledged_by = ?")
                params.append(actor)
            elif new_state == "DISMISSED":
                updates.append("dismissed_reason = ?")
                params.append(dismissed_reason)
                # Assuming dismissed implies acknowledged/resolved by same actor for simplicity in tracking?
                # Or just store who dismissed it? The schema doesn't have 'dismissed_by', but has 'resolved_by'
                # We can reuse resolved_by or just rely on 'actor' in audit logs.
                # Let's map it to resolved_by for now or add a column if strict.
                # Schema: acknowledged_by, resolved_by. No dismissed_by.
                # I'll use resolved_by for dismissal actor too as it closes the issue.
                updates.append("resolved_by = ?")
                params.append(actor)
            elif new_state == "RESOLVED":
                updates.append("resolved_by = ?")
                params.append(actor)
                updates.append("resolution_action = ?")
                params.append(resolution_action)
                if resolution_metadata:
                    updates.append("resolution_metadata = ?")
                    params.append(json.dumps(resolution_metadata))

            params.append(alert_id)
            
            query = f"UPDATE coverage_alerts SET {', '.join(updates)} WHERE alert_id = ?"
            conn.execute(query, params)
            conn.commit()
            return True
        except Exception as e:
            print(f"[AlertManager] Error transitioning alert {alert_id} to {new_state}: {e}")
            return False
        finally:
            conn.close()
