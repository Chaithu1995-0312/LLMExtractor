import logging
import sys
import os

# Add project root to sys.path so we can import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
from src.nexus.l3.clustering_engine import L3ClusteringEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("run_l3_clustering")

def main():
    load_dotenv()
    
    logger.info("Starting L3 Deterministic Clustering Run...")
    
    try:
        engine = L3ClusteringEngine()
        run_id = engine.run_clustering()
        
        if run_id:
            logger.info(f"Successfully completed clustering run. Run ID: {run_id}")
            logger.info("Check graph.node_clusters and graph.cluster_stats for results.")
        else:
            logger.error("Clustering run failed to produce a result.")
            
    except Exception as e:
        logger.exception(f"Fatal error during clustering run: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
