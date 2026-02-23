import os
from datetime import date
from nexus.db import get_adapter

class BudgetController:
    """
    Manages daily cognitive budget and dynamic thresholds.
    Refreshes state from DB on each call to handle distributed workers.
    """
    
    def __init__(self):
        self.db = get_adapter()
        # Default Limits (Can be moved to env vars)
        self.DAILY_TOKEN_LIMIT = int(os.getenv("COGNITION_TOKEN_LIMIT", "100000"))
        self.DAILY_API_LIMIT = int(os.getenv("COGNITION_API_LIMIT", "500"))

        # Base Thresholds
        self.L2_BASE_THRESHOLD = 0.75
        self.L3_BASE_THRESHOLD = 0.80

    def get_budget_pressure(self) -> float:
        """
        Calculates current budget pressure (0.0 - 1.0).
        Pressure = usage / limit.
        """
        row = self.db.fetch_one(
            "SELECT tokens_used FROM graph.cognition_budget WHERE date = CURRENT_DATE"
        )
        
        if not row:
            return 0.0
            
        used = row[0]
        pressure = used / max(self.DAILY_TOKEN_LIMIT, 1)
        return min(pressure, 1.0) # Clamp to 1.0

    def get_l2_threshold(self) -> float:
        """
        Returns dynamic L2 threshold based on budget pressure.
        Formula: Base + (0.15 * Pressure)
        Range: 0.75 -> 0.90
        """
        pressure = self.get_budget_pressure()
        return self.L2_BASE_THRESHOLD + (0.15 * pressure)

    def get_l3_threshold(self) -> float:
        """
        Returns dynamic L3 threshold.
        Formula: Base + (0.15 * Pressure)
        Range: 0.80 -> 0.95
        """
        pressure = self.get_budget_pressure()
        return self.L3_BASE_THRESHOLD + (0.15 * pressure)

    def track_usage(self, tokens: int, cost_estimate: float = 0.0):
        """
        Updates the daily budget ledger.
        Atomic increment via UPSERT.
        """
        self.db.execute(
            """
            INSERT INTO graph.cognition_budget (date, tokens_used, api_calls, estimated_cost, updated_at)
            VALUES (CURRENT_DATE, %s, 1, %s, NOW())
            ON CONFLICT (date) DO UPDATE SET
                tokens_used = graph.cognition_budget.tokens_used + EXCLUDED.tokens_used,
                api_calls = graph.cognition_budget.api_calls + 1,
                estimated_cost = graph.cognition_budget.estimated_cost + EXCLUDED.estimated_cost,
                updated_at = NOW()
            """,
            (tokens, cost_estimate)
        )
