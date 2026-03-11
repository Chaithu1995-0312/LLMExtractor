"""
nexus.cache.decision_cache
==========================
Persistent caching layer for LLM reasoning decisions.
Reduces cost and latency by reusing identical decisions.
"""

import hashlib
import json
import logging
from typing import Any, Dict, Optional, List
from datetime import timedelta

from nexus.db import get_adapter
from nexus.config import get_section_config

logger = logging.getLogger(__name__)

DEFAULT_TTL_HOURS = 168  # 7 days

class DecisionCache:
    def __init__(self):
        self.db = get_adapter()
        self.config = get_section_config("decision_cache")
        self.enabled = self.config.get("enabled", True)
        self.default_ttl = self.config.get("ttl_hours", DEFAULT_TTL_HOURS)

    def compute_key(self, agent_name: str, system_prompt: str, user_prompt: str, context_ids: Optional[List[str]] = None) -> str:
        """
        Generates a deterministic SHA-256 hash key for the decision.
        Normalizes prompts (strip/lower) to increase hit rate.
        """
        payload = {
            "agent": agent_name,
            "system_prompt": system_prompt.strip().lower(),
            "user_prompt": user_prompt.strip().lower(),
            "context": sorted(context_ids) if context_ids else []
        }
        
        # Sort keys to ensure consistent JSON serialization
        canonical_json = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a cached result if it exists and is not expired.
        """
        if not self.enabled:
            return None

        query = """
            SELECT result 
            FROM graph.decision_cache 
            WHERE cache_key = %s 
              AND (created_at + (ttl_hours || ' hours')::interval) > NOW()
        """
        
        try:
            if hasattr(self.db, 'fetch_one'):
                row = self.db.fetch_one(query, (cache_key,))
            else:
                # Raw cursor support
                self.db.execute(query, (cache_key,))
                row = self.db.fetchone()
            
            if row:
                result_json = row[0]
                return result_json if isinstance(result_json, dict) else json.loads(result_json)
                
        except Exception as e:
            logger.warning(f"[DecisionCache] Lookup failed for {cache_key}: {e}")
            
        return None

    def set(self, cache_key: str, agent_name: str, result: Dict[str, Any], ttl_hours: Optional[int] = None) -> None:
        """
        Stores a decision result in the cache.
        """
        if not self.enabled:
            return

        ttl = ttl_hours if ttl_hours is not None else self.default_ttl
        
        query = """
            INSERT INTO graph.decision_cache 
            (cache_key, agent_name, result, ttl_hours, created_at)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (cache_key) DO UPDATE SET
                result = EXCLUDED.result,
                ttl_hours = EXCLUDED.ttl_hours,
                created_at = NOW()
        """
        
        try:
            self.db.execute(
                query, 
                (cache_key, agent_name, json.dumps(result), ttl)
            )
        except Exception as e:
            logger.warning(f"[DecisionCache] Write failed for {cache_key}: {e}")

# Global singleton helper
_CACHE_INSTANCE = None

def get_decision_cache() -> DecisionCache:
    global _CACHE_INSTANCE
    if _CACHE_INSTANCE is None:
        _CACHE_INSTANCE = DecisionCache()
    return _CACHE_INSTANCE
