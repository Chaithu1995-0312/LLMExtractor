import json
from typing import Dict, Optional, Any
from nexus.db import get_adapter
from nexus.db.init_db import init_database

class GovernanceViolation(Exception):
    """Raised when a required system prompt is missing from the governance store."""
    pass

class PromptManager:
    def __init__(self, db_path: str = None):
        # db_path is ignored in Postgres implementation
        self.db = get_adapter()
        self._cache = {}
        self._init_db()

    def _init_db(self):
        """Initialize the database with the schema."""
        try:
            init_database()
        except Exception as e:
            print(f"[PromptManager] Error initializing database: {e}")

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

        if version:
            row = self.db.fetch_one(
                "SELECT content FROM governance.prompts WHERE slug = %s AND version = %s",
                (slug, version)
            )
        else:
            row = self.db.fetch_one(
                "SELECT content FROM governance.prompts WHERE slug = %s ORDER BY version DESC LIMIT 1",
                (slug,)
            )
        
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

    def save_prompt(self, slug: str, content: str, role: str = 'system', description: str = None, metadata: Any = None):
        """Saves a new prompt version."""
        # Find current max version
        row = self.db.fetch_one("SELECT MAX(version) FROM governance.prompts WHERE slug = %s", (slug,))
        next_version = (row[0] or 0) + 1
        
        self.db.execute(
            """
            INSERT INTO governance.prompts (slug, version, content, role, description, metadata, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """,
            (slug, next_version, content, role, description, json.dumps(metadata) if metadata else None)
        )
        # Invalidate cache
        self._cache.pop(f"{slug}:latest", None)
        self._cache.pop(f"{slug}:{next_version}", None)

    def get_all_system_prompts(self) -> list:
        """Retrieves latest version of all system prompts."""
        rows = self.db.fetch_all("""
            SELECT p1.slug, p1.version, p1.content, p1.role, p1.description, p1.metadata, p1.created_at
            FROM governance.prompts p1
            INNER JOIN (
                SELECT slug, MAX(version) AS max_v
                FROM governance.prompts
                GROUP BY slug
            ) p2 ON p1.slug = p2.slug AND p1.version = p2.max_v
        """)
        
        results = []
        for row in rows:
            # row is a tuple, we need to map it to dict since previously we used sqlite3.Row
            results.append({
                "slug": row[0],
                "version": row[1],
                "content": row[2],
                "role": row[3],
                "description": row[4],
                "metadata": row[5] if isinstance(row[5], dict) else json.loads(row[5] if row[5] else "{}"),
                "created_at": row[6]
            })
        return results
