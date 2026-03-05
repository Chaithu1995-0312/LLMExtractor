from nexus.db import get_adapter

def cleanup_test_artifacts():
    db = get_adapter()
    print("[Cleanup] Removing test artifacts (test_drift_%)...")
    
    with db.transaction() as cur:
        cur.execute("DELETE FROM graph.nodes WHERE id LIKE 'test_drift_%'")
        # Also clean up any edges connected to them (handled by CASCADE usually, but explicit here)
        cur.execute("DELETE FROM graph.edges WHERE source_id LIKE 'test_drift_%' OR target_id LIKE 'test_drift_%'")
        
        # Also remove intent_metrics for them
        cur.execute("DELETE FROM graph.intent_metrics WHERE intent_id LIKE 'test_drift_%'")
        
    print("[Cleanup] Complete.")

if __name__ == "__main__":
    cleanup_test_artifacts()
