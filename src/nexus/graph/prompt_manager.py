import sqlite3
import json
import os
from typing import Dict, Optional, Any
from nexus.sync.db import GRAPH_DB_PATH

class GovernanceViolation(Exception):
    """Raised when a required system prompt is missing from the governance store."""
    pass

class PromptManager:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or GRAPH_DB_PATH
        self._cache = {}

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def get_prompt(self, slug: str, version: Optional[int] = None, fallback: Optional[str] = None) -> str:
        """
        Retrieves a prompt by slug. 
        If version is None, retrieves the latest (highest version number).
        If not found in DB, returns fallback or raises GovernanceViolation.
        """
        # Governance Invariant: Approved Prompt Set (Hardcoded for now, can move to DB)
        approved_slugs = ["nexus-compiler-system", "nexus-cognition-synthesis"]
        
        cache_key = f"{slug}:{version or 'latest'}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            if version:
                cursor.execute(
                    "SELECT content FROM prompts WHERE slug = ? AND version = ?",
                    (slug, version)
                )
            else:
                cursor.execute(
                    "SELECT content FROM prompts WHERE slug = ? ORDER BY version DESC LIMIT 1",
                    (slug,)
                )
            
            row = cursor.fetchone()
            if row:
                content = row[0]
                self._cache[cache_key] = content
                return content
            
            if fallback is not None:
                # Guardrail 3: Hard fail for system-critical prompts if no fallback OR specific slugs
                critical_prompts = ["nexus-compiler-system"]
                
                # Lazy import to avoid circular dependency
                from nexus.graph.manager import GraphManager
                from nexus.graph.schema import AuditEventType, DecisionAction
                graph = GraphManager()

                if slug not in approved_slugs:
                    graph._log_audit_event(
                        event_type=AuditEventType.PROMPT_NOT_APPROVED,
                        agent="PromptManager",
                        component="governance",
                        decision_action=DecisionAction.SKIPPED,
                        reason=f"Prompt slug '{slug}' is not in the approved set.",
                        metadata={"slug": slug}
                    )

                if slug in critical_prompts and not fallback:
                     raise GovernanceViolation(f"CRITICAL PROMPT MISSING: {slug}. System cannot proceed safely.")
                
                print(f"⚠️ [PromptManager] WARN: Prompt '{slug}' not found in DB. Using hardcoded fallback.")
                
                graph._log_audit_event(
                    event_type=AuditEventType.PROMPT_FALLBACK_USED,
                    agent="PromptManager",
                    component="governance",
                    decision_action=DecisionAction.ACCEPTED,
                    reason=f"Prompt '{slug}' used hardcoded fallback.",
                    metadata={"slug": slug, "version_requested": version}
                )

                return fallback
            
            raise GovernanceViolation(f"Critical system prompt '{slug}' missing from governance store and no fallback provided.")
        
        finally:
            conn.close()

    def save_prompt(self, slug: str, content: str, role: str = 'system', description: str = None, metadata: Any = None):
        """Saves a new prompt version."""
        conn = self._get_conn()
        try:
            # Find current max version
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(version) FROM prompts WHERE slug = ?", (slug,))
            row = cursor.fetchone()
            next_version = (row[0] or 0) + 1
            
            conn.execute(
                """
                INSERT INTO prompts (slug, version, content, role, description, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (slug, next_version, content, role, description, json.dumps(metadata) if metadata else None)
            )
            conn.commit()
            # Invalidate cache
            self._cache.pop(f"{slug}:latest", None)
            self._cache.pop(f"{slug}:{next_version}", None)
        finally:
            conn.close()

    def get_all_system_prompts(self) -> list:
        """Retrieves latest version of all system prompts."""
        conn = self._get_conn()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT p1.slug, p1.version, p1.content, p1.role, p1.description, p1.metadata, p1.created_at
                FROM prompts p1
                INNER JOIN (
                    SELECT slug, MAX(version) AS max_v
                    FROM prompts
                    GROUP BY slug
                ) p2 ON p1.slug = p2.slug AND p1.version = p2.max_v
            """)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
