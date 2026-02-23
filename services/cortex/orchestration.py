import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable
from nexus.db import get_adapter

class TaskQueue:
    """
    Postgres-backed Task Queue for L3 Orchestration.
    Couples task lifecycle with graph mutations transactionally.
    """
    
    @staticmethod
    def enqueue(task_type: str, payload: Dict[str, Any], max_retries: int = 3):
        db = get_adapter()
        db.execute(
            """
            INSERT INTO graph.l3_tasks (task_type, payload, max_retries, status, scheduled_at)
            VALUES (%s, %s, %s, 'pending', NOW())
            """,
            (task_type, json.dumps(payload), max_retries)
        )
        print(f"[TaskQueue] Enqueued {task_type}")

class TaskRegistry:
    """
    Global registry of task handlers.
    """
    _handlers: Dict[str, Callable] = {}

    @classmethod
    def register(cls, task_type: str):
        def decorator(func: Callable):
            cls._handlers[task_type] = func
            return func
        return decorator

    @classmethod
    def get_handler(cls, task_type: str) -> Optional[Callable]:
        return cls._handlers.get(task_type)
