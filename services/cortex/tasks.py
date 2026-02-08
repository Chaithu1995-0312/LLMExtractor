from services.cortex.worker import celery_app
import sys
import os
import traceback

# Ensure we can import from src
try:
    from nexus.graph.manager import GraphManager
    from nexus.cognition.assembler import assemble_topic
    from nexus.cognition.synthesizer import run_relationship_synthesis
except ImportError:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    sys.path.append(os.path.join(repo_root, "src"))
    from nexus.graph.manager import GraphManager
    from nexus.cognition.assembler import assemble_topic
    from nexus.cognition.synthesizer import run_relationship_synthesis

@celery_app.task(bind=True, name="sync_bricks")
def sync_bricks_task(self):
    """
    Background task to sync bricks from ingestion to graph.
    """
    try:
        print("[Task] Starting Sync Bricks...")
        manager = GraphManager()
        manager.sync_bricks_to_nodes()
        print("[Task] Sync Bricks Completed.")
        return {"status": "success"}
    except Exception as e:
        print(f"[Task] Sync Bricks Failed: {e}")
        self.retry(exc=e, countdown=60, max_retries=3)

@celery_app.task(bind=True, name="assemble_topic")
def assemble_topic_task(self, topic: str):
    """
    Background task to assemble a topic.
    """
    try:
        print(f"[Task] Assembling Topic: {topic}")
        artifact_path = assemble_topic(topic)
        print(f"[Task] Assembly Completed: {artifact_path}")
        return {"status": "success", "artifact_path": artifact_path}
    except Exception as e:
        print(f"[Task] Assembly Failed: {e}")
        return {"status": "failed", "error": str(e)}

@celery_app.task(bind=True, name="synthesize_relationships")
def synthesize_relationships_task(self, topic_id: str = None):
    """
    Background task to discover relationships.
    """
    try:
        print(f"[Task] Synthesizing Relationships (Topic: {topic_id})...")
        count = run_relationship_synthesis(topic_id=topic_id)
        print(f"[Task] Synthesis Completed. Found {count} new edges.")
        return {"status": "success", "new_edges": count}
    except Exception as e:
        print(f"[Task] Synthesis Failed: {e}")
        return {"status": "failed", "error": str(e)}
