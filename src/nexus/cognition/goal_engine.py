import json
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from nexus.db import get_adapter
from nexus.sync.llm import LLMClient
from nexus.config import get_agent_config

class GoalEngine:
    def __init__(self, db_adapter=None, llm_client: Optional[LLMClient] = None):
        self.db = db_adapter or get_adapter()
        self.llm_client = llm_client
        self.config = get_agent_config("goal_engine") or {}
        
    def create_goal(self, description: str, priority: int = 0, metadata: Dict = None) -> str:
        """
        Creates a new goal in the graph.goals table.
        Returns the goal_id.
        """
        goal_id = str(uuid.uuid4())
        metadata = metadata or {}
        
        self.db.execute("""
            INSERT INTO graph.goals (goal_id, description, status, priority, metadata)
            VALUES (%s, %s, 'PENDING', %s, %s)
        """, (goal_id, description, priority, json.dumps(metadata)))
        
        print(f"[GoalEngine] Created goal: {description} ({goal_id})")
        return goal_id

    def run_cycle(self):
        """
        Main cognition loop:
        1. Fetch active goals (or activate pending ones)
        2. Generate tasks for them
        3. Dispatch tasks
        """
        # 1. Activate PENDING goals
        self._activate_pending_goals()
        
        # 2. Process ACTIVE goals
        goals = self.db.fetchall("""
            SELECT goal_id, description, priority, metadata 
            FROM graph.goals
            WHERE status = 'ACTIVE'
            ORDER BY priority DESC
        """)
        
        for goal in goals:
            try:
                self._process_goal(goal)
            except Exception as e:
                print(f"[GoalEngine] Failed to process goal {goal['goal_id']}: {e}")

    def _activate_pending_goals(self):
        """Moves PENDING goals to ACTIVE."""
        self.db.execute("""
            UPDATE graph.goals
            SET status = 'ACTIVE', updated_at = NOW()
            WHERE status = 'PENDING'
        """)

    def _process_goal(self, goal: Dict):
        """
        Analyzes a goal and generates sub-tasks if needed.
        This is where the 'self-improving' logic lives.
        """
        goal_id = goal['goal_id']
        description = goal['description']
        metadata = goal['metadata'] or {}
        
        # For this iteration, we implemented a simple "Research" strategy
        # If the goal is newly active and hasn't been planned, generate tasks.
        
        if metadata.get("stage") == "planned":
            return
            
        print(f"[GoalEngine] Planning for goal: {description}")
        
        # MVP: Generate a single L3 Research Task for this goal
        # In a full version, this would use an LLM to decompose the goal.
        
        task_payload = {
            "goal_id": goal_id,
            "instruction": f"Execute goal: {description}",
            "context": metadata
        }
        
        self._schedule_task(
            task_type="goal_reasoning",
            payload=task_payload
        )
        
        # Mark as planned
        metadata["stage"] = "planned"
        self.db.execute("""
            UPDATE graph.goals
            SET metadata = %s, updated_at = NOW()
            WHERE goal_id = %s
        """, (json.dumps(metadata), goal_id))

    def _schedule_task(self, task_type: str, payload: Dict):
        """
        Inserts a task into graph.l3_tasks for the worker to pick up.
        """
        task_id = str(uuid.uuid4())
        # Use execute (not fetchall) for INSERT
        self.db.execute("""
            INSERT INTO graph.l3_tasks (id, task_type, payload, status, priority, attempts, max_retries, scheduled_at)
            VALUES (%s, %s, %s, 'pending', 10, 0, 3, NOW())
        """, (task_id, task_type, json.dumps(payload)))
        
        print(f"[GoalEngine] Scheduled task {task_type} for goal")
