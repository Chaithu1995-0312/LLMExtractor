-- L3 Clustering Schema (Idempotent)
-- Purpose: Versioned unsupervised clustering runs and metrics.

CREATE TABLE IF NOT EXISTS graph.cluster_runs (
    id UUID PRIMARY KEY,
    algorithm TEXT NOT NULL,
    metric TEXT NOT NULL,
    min_cluster_size INTEGER NOT NULL,
    min_samples INTEGER NOT NULL,
    embedding_model TEXT NOT NULL,
    node_count INTEGER NOT NULL,
    cluster_count INTEGER NOT NULL,
    noise_count INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS graph.node_clusters (
    cluster_run_id UUID REFERENCES graph.cluster_runs(id) ON DELETE CASCADE,
    node_id TEXT REFERENCES graph.nodes(id) ON DELETE CASCADE,
    cluster_id TEXT, -- formatted as cluster_{run_short}_{index}
    confidence FLOAT,
    PRIMARY KEY (cluster_run_id, node_id)
);

-- Ensure cluster_stats has the correct structure for this version of L3
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'cluster_stats' AND table_schema = 'graph') THEN
        CREATE TABLE graph.cluster_stats (
            cluster_run_id UUID REFERENCES graph.cluster_runs(id) ON DELETE CASCADE,
            cluster_id TEXT NOT NULL,
            node_count INTEGER NOT NULL,
            lifecycle_distribution JSONB NOT NULL,
            kill_ratio FLOAT NOT NULL,
            stability_index FLOAT NOT NULL,
            keywords TEXT[],
            PRIMARY KEY (cluster_run_id, cluster_id)
        );
    ELSE
        -- If it exists, ensure it has cluster_run_id (handle collision with any legacy schema)
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'cluster_stats' AND column_name = 'cluster_run_id') THEN
            DROP TABLE graph.cluster_stats; -- Destructive but necessary if schema mismatch in development
            CREATE TABLE graph.cluster_stats (
                cluster_run_id UUID REFERENCES graph.cluster_runs(id) ON DELETE CASCADE,
                cluster_id TEXT NOT NULL,
                node_count INTEGER NOT NULL,
                lifecycle_distribution JSONB NOT NULL,
                kill_ratio FLOAT NOT NULL,
                stability_index FLOAT NOT NULL,
                keywords TEXT[],
                PRIMARY KEY (cluster_run_id, cluster_id)
            );
        END IF;
    END IF;
END $$;

-- Indexes for fast retrieval of latest clustering run
CREATE INDEX IF NOT EXISTS idx_node_clusters_node_id ON graph.node_clusters(node_id);
CREATE INDEX IF NOT EXISTS idx_cluster_stats_run_id ON graph.cluster_stats(cluster_run_id);
