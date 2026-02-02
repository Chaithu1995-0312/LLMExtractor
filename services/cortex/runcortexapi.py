from api import CortexAPI

cortex = CortexAPI()

result = cortex.generate(
    user_id="test_user",
    agent_id="Architect",
    user_query="Explain Nexus architecture",
    brick_ids=["brick_001"]
)

print(result)
