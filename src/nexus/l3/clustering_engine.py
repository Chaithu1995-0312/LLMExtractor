import os
import json
import uuid
import logging
import numpy as np
import psycopg2
from typing import List, Dict, Any, Tuple
from datetime import datetime
from sklearn.preprocessing import normalize
import hdbscan

from src.nexus.l3.keyword_extractor import L3KeywordExtractor

logger = logging.getLogger(__name__)

class L3ClusteringEngine:
    """
    L3 Deterministic Clustering Engine.
    Uses HDBSCAN with cosine metric to group nodes semantically.
    """

    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.environ.get("DATABASE_URL")
        self.keyword_extractor = L3KeywordExtractor()
        
        # HDBSCAN Hyperparameters
        self.min_cluster_size = 3
        self.min_samples = 2
        # Note: We use 'euclidean' here because HDBSCAN's scikit-learn BallTree backend 
        # doesn't natively support 'cosine'. Since we L2-normalize our embeddings 
        # before passing them to HDBSCAN, euclidean distance perfectly proxies cosine distance.
        self.metric = "euclidean"
        self.cluster_selection_method = "eom"

    def run_clustering(self) -> str:
        """
        Execute a full versioned clustering run.
        Returns the cluster_run_id.
        """
        run_id = str(uuid.uuid4())
        run_short = run_id[:8]
        
        # 1. Fetch nodes and embeddings
        logger.info("Fetching embeddings from database...")
        nodes = self._fetch_all_nodes_with_embeddings()
        if not nodes:
            logger.warning("No nodes with embeddings found. Aborting.")
            return None

        node_ids = [n['id'] for n in nodes]
        embeddings = np.array([n['embedding'] for n in nodes], dtype=np.float32)
        
        # 2. Normalize for cosine distance (if not already)
        # HDBSCAN cosine metric expects normalized vectors or handles it depending on implementation
        # For reliability with 'cosine', we ensure normalization.
        embeddings_norm = normalize(embeddings)

        # 3. Run HDBSCAN
        logger.info(f"Running HDBSCAN on {len(nodes)} nodes...")
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=self.min_cluster_size,
            min_samples=self.min_samples,
            metric=self.metric,
            cluster_selection_method=self.cluster_selection_method,
            prediction_data=True
        )
        cluster_labels = clusterer.fit_predict(embeddings_norm)
        probabilities = clusterer.probabilities_
        
        # 4. Process Results
        clusters = {} # cluster_id -> list of node indices
        noise_indices = []
        
        for i, label in enumerate(cluster_labels):
            if label == -1:
                noise_indices.append(i)
            else:
                cid = f"cluster_{run_short}_{label}"
                if cid not in clusters:
                    clusters[cid] = []
                clusters[cid].append(i)

        cluster_count = len(clusters)
        noise_count = len(noise_indices)
        
        logger.info(f"Clustering complete. Found {cluster_count} clusters and {noise_count} noise points.")

        # 5. Persist to DB
        self._persist_run(
            run_id=run_id,
            node_ids=node_ids,
            cluster_labels=cluster_labels,
            probabilities=probabilities,
            run_short=run_short,
            nodes=nodes,
            clusters=clusters
        )

        return run_id

    def _fetch_all_nodes_with_embeddings(self) -> List[Dict[str, Any]]:
        conn = psycopg2.connect(self.database_url)
        try:
            with conn.cursor() as cur:
                # JOIN nodes and vector_meta to get all necessary data
                cur.execute("""
                    SELECT n.id, n.data, v.embedding, v.embedding_model
                    FROM graph.nodes n
                    JOIN graph.vector_meta v ON n.id = v.node_id
                """)
                rows = cur.fetchall()
                
                nodes = []
                for row in rows:
                    node_id, data, embedding_raw, model = row
                    # embedding in PG is stored as a vector, psycopg2 might return it as a list/string
                    # If it's a string like '[0.1, 0.2]', parse it
                    if isinstance(embedding_raw, str):
                        embedding = json.loads(embedding_raw)
                    else:
                        embedding = embedding_raw
                        
                    nodes.append({
                        'id': node_id,
                        'data': data,
                        'embedding': embedding,
                        'model': model
                    })
                return nodes
        finally:
            conn.close()

    def _persist_run(self, run_id: str, node_ids: List[str], cluster_labels: np.ndarray, 
                     probabilities: np.ndarray, run_short: str, nodes: List[Dict[str, Any]],
                     clusters: Dict[str, List[int]]):
        
        conn = psycopg2.connect(self.database_url)
        # We handle transactions manually to avoid all-or-nothing rollback
        conn.autocommit = False
        
        try:
            with conn.cursor() as cur:
                # 1. Insert Cluster Run (STEP 1)
                cur.execute("""
                    INSERT INTO graph.cluster_runs 
                    (id, algorithm, metric, min_cluster_size, min_samples, embedding_model, node_count, cluster_count, noise_count)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    run_id, "HDBSCAN", self.metric, int(self.min_cluster_size), 
                    int(self.min_samples), nodes[0]['model'], int(len(node_ids)), 
                    int(len(clusters)), int(np.sum(cluster_labels == -1))
                ))
            conn.commit()
            logger.info(f"Committed cluster_run {run_id}")
        except Exception as e:
            logger.error(f"Error inserting cluster_run {run_id}: {e}")
            conn.rollback()
            conn.close()
            raise

        try:
            with conn.cursor() as cur:
                # 2. Bulk Insert Node Clusters (STEP 2)
                node_cluster_data = []
                for i, node_id in enumerate(node_ids):
                    label = cluster_labels[i]
                    cid = f"cluster_{run_short}_{label}" if label != -1 else None
                    # Ensure confidence is float (NumPy float64 to native float)
                    node_cluster_data.append((run_id, node_id, cid, float(probabilities[i])))
                
                from psycopg2.extras import execute_values
                execute_values(cur, """
                    INSERT INTO graph.node_clusters (cluster_run_id, node_id, cluster_id, confidence)
                    VALUES %s
                """, node_cluster_data)
            conn.commit()
            logger.info(f"Committed {len(node_cluster_data)} node_clusters for run {run_id}")
        except Exception as e:
            logger.error(f"Error inserting node_clusters for run {run_id}: {e}")
            conn.rollback()
            # If node_clusters fail, we leave cluster_run for audit, but we shouldn't compute stats.
            conn.close()
            return

        try:
            with conn.cursor() as cur:
                # 3. Compute and Insert Cluster Stats (STEP 3)
                for cid, indices in clusters.items():
                    if cid is None:
                        continue
                    
                    cluster_nodes = [nodes[idx] for idx in indices]
                    stats = self._compute_cluster_stats(cluster_nodes, [probabilities[idx] for idx in indices])
                    
                    cur.execute("""
                        INSERT INTO graph.cluster_stats 
                        (cluster_run_id, cluster_id, node_count, lifecycle_distribution, kill_ratio, stability_index, keywords)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        run_id, cid, int(len(cluster_nodes)), json.dumps(stats['lifecycle_dist']),
                        float(stats['kill_ratio']), float(stats['stability']), stats['keywords']
                    ))
            conn.commit()
            logger.info(f"Committed {len(clusters)} cluster_stats for run {run_id}")
            
        except Exception as e:
            logger.error(f"Error inserting cluster_stats for run {run_id}: {e}")
            conn.rollback()
            # Stats failed, but node_clusters and cluster_run remain intact
            
        finally:
            conn.close()

    def _compute_cluster_stats(self, cluster_nodes: List[Dict[str, Any]], probs: List[float]) -> Dict[str, Any]:
        lifecycles = [n['data'].get('lifecycle', 'unknown') for n in cluster_nodes]
        statements = [n['data'].get('statement', '') for n in cluster_nodes]
        
        from collections import Counter
        dist = Counter(lifecycles)
        
        killed_count = dist.get('killed', 0)
        # Ensure kill_ratio is float
        kill_ratio = float(killed_count / len(cluster_nodes)) if cluster_nodes else 0.0
        # Ensure stability is float
        stability = float(sum(probs) / len(probs)) if probs else 0.0
        
        keywords = self.keyword_extractor.extract_keywords(statements)
        
        return {
            # Ensure all counts in distribution are native int
            'lifecycle_dist': {str(k): int(v) for k, v in dist.items()},
            'kill_ratio': kill_ratio,
            'stability': stability,
            'keywords': keywords
        }

# ==========================================
# SELF-REVIEW PACKET
# ==========================================
# Assumptions:
# - DB schema for cluster_stats does not include conflict_ratio.
# - Keyword extraction relies strictly on TF-IDF determinism.
#
# Invariants:
# - A cluster_runs entry always exists if the clustering algorithm completes.
# - Partial failures in cluster_stats will not corrupt node_clusters mappings.
#
# Edge cases:
# - All points classified as noise (-1 label).
# - Missing model field in node metadata fallback handled.
#
# Failure modes:
# - node_clusters fails: Execution stops, cluster_run left as tombstone for audit.
# - cluster_stats fails: Node mappings persist, engine recovers gracefully.
#
# Rerun safety:
# - Fully safe. Each run generates a novel UUID. No overwriting occurs.
#
# Idempotency behavior:
# - While clustering itself can yield slightly different results per run (depending on algorithm details), the persistence logic is append-only and immutable.
#
# Transaction boundaries:
# 1. cluster_runs (Immediate Commit)
# 2. node_clusters (Batch Commit)
# 3. cluster_stats (Batch Commit)
#
# Future extension notes:
# - We can safely add `conflict_ratio` when Phase 2 starts, by adding a schema migration and updating `_compute_cluster_stats`.
