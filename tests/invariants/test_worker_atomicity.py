import unittest
import json
from services.cortex.orchestration import TaskQueue, TaskRegistry
from nexus.db import get_adapter
from nexus.graph.manager import GraphManager

# A mock task handler that will fail
def failing_task_handler(payload, cursor):
    # Perform a graph mutation
    GraphManager(db=cursor).register_node("test", "test_node_1", {"status": "created"})
    # Then fail
    raise ValueError("Simulating task failure")

TaskRegistry.register("failing_task")(failing_task_handler)

class TestWorkerAtomicity(unittest.TestCase):
    def setUp(self):
        self.db = get_adapter()
        self.worker = self.create_worker()
        self.clear_queue()

    def create_worker(self):
        # Dynamically import PGWorker to avoid circular dependencies
        from services.cortex.worker import PGWorker
        return PGWorker()

    def clear_queue(self):
        self.db.execute("DELETE FROM graph.l3_tasks")
        self.db.execute("DELETE FROM graph.nodes WHERE id = 'test_node_1'")

    def test_failed_task_rolls_back_mutation(self):
        # Enqueue the failing task
        TaskQueue.enqueue("failing_task", {})
        
        # Run the worker, which should process the task and fail
        self.worker.run_once()
        
        # Check task status
        task = self.db.fetch_one("SELECT status, attempts FROM graph.l3_tasks")
        self.assertEqual(task[0], "pending") # Should be reset to pending for retry
        self.assertEqual(task[1], 1)
        
        # Check for partial graph mutation
        node = self.db.fetch_one("SELECT id FROM graph.nodes WHERE id = 'test_node_1'")
        self.assertIsNone(node)

if __name__ == "__main__":
    unittest.main()
