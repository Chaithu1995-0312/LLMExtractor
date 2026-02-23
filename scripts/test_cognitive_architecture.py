import os
import sys

# Add src to path to allow imports
sys.path.append(os.path.join(os.getcwd(), 'src'))

from dotenv import load_dotenv
load_dotenv()

from nexus.cognition.l2_narrator import L2Narrator
from nexus.cognition.l3_sage import L3Sage
from nexus.cognition.budget_controller import BudgetController

def test_full_cognitive_stack():
    print("="*60)
    print("  TESTING COGNITIVE ARCHITECTURE (HYBRID V2)")
    print("="*60)
    
    # 1. Budget Check
    print("\n[TEST] 1. Budget Controller...")
    budget = BudgetController()
    pressure = budget.get_budget_pressure()
    print(f"   -> Current Budget Pressure: {pressure:.2f}")
    print(f"   -> Dynamic L2 Threshold: {budget.get_l2_threshold():.2f}")
    
    # 2. L2 Narrator (Hybrid)
    print("\n[TEST] 2. L2 Narrator (Hybrid Escalation)...")
    l2 = L2Narrator()
    
    old_brick = {"id": "test_old", "content": "The system uses simple file storage.", "topic_id": "test-arch"}
    new_brick = {"id": "test_new", "content": "The system uses distributed PostgreSQL for ACID compliance.", "topic_id": "test-arch"}
    
    explanation = l2.explain_supersession(old_brick, new_brick)
    print(f"   -> Explanation Result:\n{explanation[:100]}...")
    
    # 3. L3 Sage (Audit)
    print("\n[TEST] 3. L3 Sage (Strategic Audit)...")
    l3 = L3Sage()
    # Using existing topic from previous runs if available
    topic_id = "nexus-server-sync"
    
    audit_result = l3.audit_topic_health(topic_id)
    print(f"   -> Audit Result Keys: {list(audit_result.keys())}")
    print(f"   -> Risk Score: {audit_result.get('risk_score')}")

    print("\n[TEST] Success. Full stack initialized and executed.")

if __name__ == "__main__":
    test_full_cognitive_stack()
