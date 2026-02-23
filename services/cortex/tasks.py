from services.cortex.orchestration import TaskRegistry
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

@TaskRegistry.register("process_drift")
def process_drift_task(payload: dict, cursor=None):
    """
    Transactional task to process semantic drift for a new node.
    """
    node_id = payload.get("node_id")
    print(f"[Task] Processing Drift for Node: {node_id}")
    engine = DriftEngine(db=cursor)
    engine.process_node(node_id)
    return {"status": "success"}

@TaskRegistry.register("compute_evolution_metrics")
def compute_evolution_metrics_task(payload: dict, cursor=None):
    """
    Transactional task to compute evolution stability metrics.
    """
    # Note: If cursor is provided, it's already in a transaction.
    # Postgres doesn't allow SET TRANSACTION ISOLATION LEVEL inside a started transaction block easily
    # if it's not the first statement. Since PGWorker starts the transaction, we rely on default level
    # or the worker should set it. For now, we proceed with the worker's transaction.
    
    cur = cursor
    
    # 1. GLOBAL METRICS
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

    # 2. CLUSTER METRICS
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
    cluster_info = cur.fetchall()
    
    for cid, node_count, edge_count in cluster_info:
        volatility = 0.0 
        depth = depth_map.get(cid, 1)
        
        cur.execute("""
            SELECT COUNT(*) FROM graph.edges e
            JOIN graph.nodes n ON e.source_id = n.id
            WHERE n.data->>'cluster_id' = %s AND e.edge_type = 'CONFLICTS_WITH'
        """, (cid,))
        conflict_count = cur.fetchone()[0]
        conflict_ratio = float(conflict_count) / float(max(edge_count, 1))

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

    return {"status": "success"}

@TaskRegistry.register("sync_bricks")
def sync_bricks_task(payload: dict, cursor=None):
    """
    Transactional task to sync bricks from ingestion to graph.
    """
    print("[Task] Starting Sync Bricks...")
    # GraphManager currently manages its own adapter/transactions in __init__.
    # To be fully transactional with PGWorker, we'd need to inject the cursor into GraphManager.
    # For now, GraphManager.sync_bricks_to_nodes is internal-transactional.
    manager = GraphManager()
    manager.sync_bricks_to_nodes()
    return {"status": "success"}

@TaskRegistry.register("assemble_topic")
def assemble_topic_task(payload: dict, cursor=None):
    """
    Transactional task to assemble a topic.
    """
    topic = payload.get("topic")
    print(f"[Task] Assembling Topic: {topic}")
    # assemble_topic creates its own GraphManager.
    artifact_path = assemble_topic(topic)
    return {"status": "success", "artifact_path": artifact_path}

@TaskRegistry.register("synthesize_relationships")
def synthesize_relationships_task(payload: dict, cursor=None):
    """
    Transactional task to discover relationships.
    """
    topic_id = payload.get("topic_id")
    print(f"[Task] Synthesizing Relationships (Topic: {topic_id})...")
    count = run_relationship_synthesis(topic_id=topic_id)
    return {"status": "success", "new_edges": count}
