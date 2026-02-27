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
    from nexus.vector.embedding_service import EmbeddingService
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
    from nexus.vector.embedding_service import EmbeddingService
    import numpy as np

@TaskRegistry.register("index_node")
def process_index_task(payload: dict, cursor=None):
    """
    Phase 2: Dedicated indexing task — decoupled from drift processing.

    Responsibility:
      1. Fetch the raw node (require_indexed=False — this is the indexer).
      2. Generate embedding via EmbeddingService.
      3. Upsert vector into VectorStore.
      4. Set vector_status = 'indexed' in graph.nodes.
      5. Schedule process_drift for this node.

    Contract:
      - Idempotent: if node is already indexed, skips embedding + vector write
        and still schedules process_drift (so a crashed mid-flight task heals).
      - If the node does not exist or has no statement, returns success (no-op).
      - If the node lifecycle is 'superseded', skip — no drift needed.
    """
    node_id = payload.get("node_id")
    if not node_id:
        return {"status": "skipped", "reason": "no node_id"}

    print(f"[Task:index_node] Indexing node: {node_id}")

    db = get_adapter()
    embedding_service = EmbeddingService()
    vector_store = VectorStore()

    # 1. Fetch node data (no vector_status filter — this IS the indexer)
    row = db.fetch_one(
        "SELECT data FROM graph.nodes WHERE id = %s",
        (node_id,)
    )
    if not row:
        print(f"[Task:index_node] Node {node_id} not found. Skipping.")
        return {"status": "skipped", "reason": "node_not_found"}

    node_data = row[0] if isinstance(row[0], dict) else __import__("json").loads(row[0])

    # Lifecycle guard: skip superseded nodes
    if node_data.get("lifecycle") == "superseded":
        print(f"[Task:index_node] Node {node_id} is superseded. Skipping.")
        return {"status": "skipped", "reason": "superseded"}

    statement = node_data.get("statement")
    if not statement:
        print(f"[Task:index_node] Node {node_id} has no statement. Skipping.")
        return {"status": "skipped", "reason": "no_statement"}

    # 2. Idempotency check — skip vector write if already indexed
    already_indexed = vector_store.exists(node_id)

    if not already_indexed:
        # 3. Generate embedding
        vector = embedding_service.embed(statement)

        # 4. Store vector — raises on failure (caller rolls back)
        vector_store.add(node_id, vector)

        # 5. Record vector_meta
        db.execute(
            """
            INSERT INTO graph.vector_meta (node_id, embedding_model, embedding_version, indexed_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (node_id) DO UPDATE SET
                embedding_model = EXCLUDED.embedding_model,
                embedding_version = EXCLUDED.embedding_version,
                indexed_at = NOW()
            """,
            (node_id, embedding_service.model_name, embedding_service.model_version())
        )

        # 6. Persist to disk immediately
        vector_store.save()

        # 7. Flip vector_status = 'indexed' — visibility gate.
        # Only flip AFTER all three writes above have succeeded.
        # Order: add() ✓ → vector_meta ✓ → save() ✓ → vector_status=indexed
        db.execute(
            "UPDATE graph.nodes "
            "SET data = jsonb_set(data, '{vector_status}', '\"indexed\"') "
            "WHERE id = %s",
            (node_id,)
        )
        print(f"[Task:index_node] Node {node_id} indexed (vector_status=indexed).")
    else:
        print(f"[Task:index_node] Node {node_id} already indexed. Skipping vector write.")

    # 8. Schedule process_drift — always, even on idempotent path
    # (covers crashed tasks that indexed but failed to enqueue drift)
    try:
        from services.cortex.orchestration import TaskQueue
        TaskQueue.enqueue("process_drift", {"node_id": node_id})
        print(f"[Task:index_node] Scheduled process_drift for node {node_id}.")
    except Exception as e:
        print(f"[Task:index_node] Warning: Failed to enqueue process_drift: {e}")
        raise  # Propagate so the task retries

    return {"status": "success", "already_indexed": already_indexed}


@TaskRegistry.register("process_drift")
def process_drift_task(payload: dict, cursor=None):
    """
    Transactional task to process semantic drift for a new node.

    Phase 2 contract: This task now REQUIRES vector_status='indexed'.
    If the node is not yet indexed (vector_status='pending'), it returns
    early with a clear signal. The node will be retried via index_node
    which schedules process_drift after indexing completes.

    Legacy path: Nodes indexed by the old monolithic flow (pre-Phase 2)
    may reach here with vector_status already set to 'indexed' inside
    DriftEngine.process_node. That path remains functional during migration.
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


# =============================================================================
# COGNITIVE COMPILER TASKS (Spec §9)
# =============================================================================

@TaskRegistry.register("compile_topic_document")
def compile_topic_document_task(payload: dict, cursor=None):
    """
    Deterministic document compilation task.

    Compiles a Topic's graph state into a StructuredDocument and
    optionally persists a versioned snapshot.

    Payload keys:
        topic_id        (str, required)  — graph.nodes ID of the topic node.
        save_snapshot   (bool, optional) — default True.

    This task is READ-ONLY with respect to the graph.  It ONLY writes to
    cognition.topic_snapshots and cognition.compiler_runs, which are
    part of the Cognitive Compiler extension — not the core graph.

    Atomicity note: The cursor injected by PGWorker is used only for
    task status updates.  The DocumentCompiler uses the shared DB adapter
    for its own reads/writes (cognition schema) to keep concerns separate.
    Snapshot persistence is idempotent (ON CONFLICT DO NOTHING).
    """
    topic_id = payload.get("topic_id")
    save_snapshot = payload.get("save_snapshot", True)

    if not topic_id:
        return {"status": "skipped", "reason": "no topic_id in payload"}

    print(f"[Task:compile_topic_document] Compiling topic: {topic_id}, snapshot={save_snapshot}")

    try:
        from nexus.projection.document_compiler import DocumentCompiler
        compiler = DocumentCompiler(db=get_adapter(), persist_snapshots=True)

        if save_snapshot:
            doc = compiler.compile_and_snapshot(topic_id)
        else:
            doc = compiler.compile_topic(topic_id)

        print(
            f"[Task:compile_topic_document] Done. "
            f"topic={topic_id} sections={len(doc.sections)} hash={doc.hash[:16]}…"
        )
        return {
            "status": "success",
            "topic_id": topic_id,
            "hash": doc.hash,
            "version": doc.version,
            "section_count": len(doc.sections),
            "snapshot_saved": save_snapshot,
        }
    except ValueError as ve:
        # Topic not found — do not retry
        print(f"[Task:compile_topic_document] Topic not found: {ve}")
        return {"status": "skipped", "reason": str(ve)}
    except Exception as e:
        print(f"[Task:compile_topic_document] Error: {e}")
        raise  # PGWorker will retry


@TaskRegistry.register("run_refiner_audit")
def run_refiner_audit_task(payload: dict, cursor=None):
    """
    Safe Refiner advisory audit task.

    Runs all drift heuristics against a topic and persists advisory
    DriftReport rows to cognition.drift_reports.

    INVARIANT: This task NEVER calls supersede_node(), kill_node(), or
    any other graph mutation.  It is purely advisory.

    Payload keys:
        topic_id  (str, required) — graph.nodes ID of the topic node.

    Atomicity note: DriftReport persistence uses direct DB inserts to
    cognition.drift_reports.  These writes are independent of the
    PGWorker's task-management transaction so a refiner failure does NOT
    roll back already-persisted reports from the same run.  This is
    intentional — partial advisory output is better than none.
    """
    topic_id = payload.get("topic_id")

    if not topic_id:
        return {"status": "skipped", "reason": "no topic_id in payload"}

    print(f"[Task:run_refiner_audit] Auditing topic: {topic_id}")

    try:
        from nexus.cognition.refiner import Refiner
        refiner = Refiner(db=get_adapter())
        reports = refiner.audit_topic(topic_id)

        severity_summary = {}
        for r in reports:
            severity_summary[r.issue_type] = severity_summary.get(r.issue_type, 0) + 1

        print(
            f"[Task:run_refiner_audit] Done. "
            f"topic={topic_id} reports={len(reports)} summary={severity_summary}"
        )
        return {
            "status": "success",
            "topic_id": topic_id,
            "report_count": len(reports),
            "summary": severity_summary,
        }
    except Exception as e:
        print(f"[Task:run_refiner_audit] Error: {e}")
        raise  # PGWorker will retry
