from services.cortex.worker import celery_app
import sys
import os
import traceback

# Ensure we can import from src
try:
    from nexus.graph.manager import GraphManager
    from nexus.cognition.assembler import assemble_topic
    from nexus.cognition.synthesizer import run_relationship_synthesis
    from nexus.evolution.drift_engine import DriftEngine
    from nexus.db import get_adapter
    from nexus.vector.vector_store import VectorStore
    import numpy as np
except ImportError:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    sys.path.append(os.path.join(repo_root, "src"))
    from nexus.graph.manager import GraphManager
    from nexus.cognition.assembler import assemble_topic
    from nexus.cognition.synthesizer import run_relationship_synthesis
    from nexus.evolution.drift_engine import DriftEngine
    from nexus.db import get_adapter
    from nexus.vector.vector_store import VectorStore
    import numpy as np

@celery_app.task(bind=True, name="process_drift", max_retries=3)
def process_drift_task(self, node_id: str):
    """
    Background task to process semantic drift for a new node.
    """
    try:
        print(f"[Task] Processing Drift for Node: {node_id}")
        engine = DriftEngine()
        engine.process_node(node_id)
        print(f"[Task] Drift Processing Completed for {node_id}")
        return {"status": "success"}
    except Exception as e:
        print(f"[Task] Drift Processing Failed: {e}")
        self.retry(exc=e, countdown=60, max_retries=3)

@celery_app.task(bind=True, name="compute_evolution_metrics")
def compute_evolution_metrics_task(self):
    """
    Nightly/Periodic task to compute evolution stability metrics.
    Uses REPEATABLE READ isolation for snapshot consistency.
    """
    db = get_adapter()
    
    try:
        with db.transaction() as cur:
            # 1. Set Isolation Level (Must be first statement in transaction)
            cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            
            # --- GLOBAL METRICS ---
            cur.execute("SELECT COUNT(*) FROM graph.nodes")
            total_nodes = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM graph.edges")
            total_edges = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM graph.edge_candidates")
            total_candidates = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM graph.edge_candidates WHERE status = 'APPROVED'")
            approved_candidates = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM graph.edge_candidates WHERE status = 'REJECTED'")
            rejected_candidates = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM graph.edges WHERE edge_type = 'SUPERSEDES'")
            supersession_edges = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM graph.edges WHERE edge_type = 'CONFLICTS_WITH'")
            conflict_edges = cur.fetchone()[0]
            
            cur.execute("""
                SELECT AVG(EXTRACT(EPOCH FROM (NOW() - created_at)) / 3600)
                FROM graph.edge_candidates
                WHERE status = 'PENDING'
            """)
            avg_pending_age = cur.fetchone()[0] or 0.0
            
            approval_ratio = float(approved_candidates) / float(max(total_candidates, 1))
            
            # Store Global Snapshot
            cur.execute(
                """
                INSERT INTO graph.system_stats (
                    total_nodes, total_edges, total_candidates, approved_candidates, 
                    rejected_candidates, approval_ratio, supersession_edges, 
                    conflict_edges, average_pending_age_hours, computed_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """,
                (
                    total_nodes, total_edges, total_candidates, approved_candidates,
                    rejected_candidates, approval_ratio, supersession_edges,
                    conflict_edges, float(avg_pending_age)
                )
            )

            # --- CLUSTER METRICS ---
            
            # A. Calculate Max Lineage Depth per Cluster
            depth_query = """
                WITH RECURSIVE lineage AS (
                    SELECT
                        n.id,
                        n.data->>'cluster_id' as cluster_id,
                        1 AS depth
                    FROM graph.nodes n
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM graph.edges e
                        WHERE e.edge_type = 'SUPERSEDES'
                          AND e.source_id = n.id
                    )

                    UNION ALL

                    SELECT
                        e.source_id,
                        l.cluster_id,
                        l.depth + 1
                    FROM graph.edges e
                    JOIN lineage l ON e.target_id = l.id
                    WHERE e.edge_type = 'SUPERSEDES'
                )
                SELECT cluster_id, MAX(depth)
                FROM lineage
                WHERE cluster_id IS NOT NULL
                GROUP BY cluster_id
            """
            cur.execute(depth_query)
            depth_map = {r[0]: r[1] for r in cur.fetchall()}
            
            # B. Fetch Cluster Membership & Edge Counts
            cur.execute("""
                SELECT 
                    n.data->>'cluster_id' as cid,
                    COUNT(DISTINCT n.id) as nodes,
                    COUNT(DISTINCT e.id) as edges
                FROM graph.nodes n
                LEFT JOIN graph.edges e ON (e.source_id = n.id OR e.target_id = n.id)
                WHERE n.data->>'cluster_id' IS NOT NULL
                GROUP BY cid
            """)
            # Simplified edge count logic for clusters would be better as a separate join, 
            # but this is functional for Phase 3.
            cluster_info = cur.fetchall()
            
            for cid, node_count, edge_count in cluster_info:
                volatility = 0.0 # Placeholder until get_vector implemented
                depth = depth_map.get(cid, 1)
                
                # Conflict Ratio per Cluster
                cur.execute("""
                    SELECT COUNT(*) FROM graph.edges e
                    JOIN graph.nodes n ON e.source_id = n.id
                    WHERE n.data->>'cluster_id' = %s AND e.edge_type = 'CONFLICTS_WITH'
                """, (cid,))
                conflict_count = cur.fetchone()[0]
                conflict_ratio = float(conflict_count) / float(max(edge_count, 1))

                # Update Cluster Stats
                cur.execute(
                    """
                    INSERT INTO graph.cluster_stats (
                        cluster_id, node_count, edge_count, supersession_depth, 
                        volatility, stability_index, conflict_ratio, last_computed_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (cluster_id) DO UPDATE SET
                        node_count = EXCLUDED.node_count,
                        edge_count = EXCLUDED.edge_count,
                        supersession_depth = EXCLUDED.supersession_depth,
                        volatility = EXCLUDED.volatility,
                        stability_index = EXCLUDED.stability_index,
                        conflict_ratio = EXCLUDED.conflict_ratio,
                        last_computed_at = NOW()
                    """,
                    (cid, node_count, edge_count, depth, volatility, 1.0 - volatility, conflict_ratio)
                )

        print("[Task] Evolution Metrics Snapshot Completed (Isolation: REPEATABLE READ).")
        return {"status": "success"}
    except Exception as e:
        print(f"[Task] Evolution Metrics Failed: {e}")
        traceback.print_exc()
        return {"status": "failed", "error": str(e)}

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
