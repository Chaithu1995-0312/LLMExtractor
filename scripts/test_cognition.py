import os
import sys

# Add src to path to allow imports
sys.path.append(os.path.join(os.getcwd(), 'src'))

from dotenv import load_dotenv
load_dotenv()

from nexus.cognition.l2_narrator import L2Narrator
from nexus.cognition.l3_sage import L3Sage

def test_cognition_modules():
    print("[TEST] Initializing L2 Narrator...")
    l2 = L2Narrator()
    
    print("[TEST] Initializing L3 Sage...")
    l3 = L3Sage()
    
    # Mock Data for L2
    old_brick = {"id": "brick_001", "content": "The system uses SQLite.", "topic_id": "test-topic"}
    new_brick = {"id": "brick_002", "content": "The system uses PostgreSQL for scalability.", "topic_id": "test-topic"}
    
    print("\n[TEST] Running L2 Explain Supersession...")
    explanation = l2.explain_supersession(old_brick, new_brick)
    print(f"[TEST] L2 Explanation:\n{explanation}")

    # Mock Audit for L3
    print("\n[TEST] Running L3 Audit (Dry Run with Mock Topic)...")
    # Using 'nexus-server-sync' as it likely exists from previous sync
    audit = l3.audit_topic_health("nexus-server-sync")
    print(f"[TEST] L3 Audit Result:\n{audit}")

if __name__ == "__main__":
    test_cognition_modules()
