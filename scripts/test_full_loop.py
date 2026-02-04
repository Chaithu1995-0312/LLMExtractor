from services.cortex.api import CortexAPI
from nexus.ask.recall import recall_bricks_readonly

def main():
    api = CortexAPI()
    query = "machine learning"
    
    print(f"Recalling for: {query}")
    # Simulate recall step (Cortex usually does this or Agent does)
    bricks = recall_bricks_readonly(query, k=1)
    if not bricks:
        print("No bricks found!")
        return

    brick_ids = [b["brick_id"] for b in bricks]
    print(f"Found bricks: {brick_ids}")
    
    # Call generate
    print("Calling generate...")
    resp = api.generate(
        user_id="test_user_p3",
        agent_id="TestAgent",
        user_query=query,
        brick_ids=brick_ids
    )
    print("Response:", resp)

if __name__ == "__main__":
    main()
