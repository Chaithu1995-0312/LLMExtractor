from nexus.orchestration.query_orchestrator import QueryOrchestrator
import json

def test_intent_query():
    orchestrator = QueryOrchestrator()
    
    print("\n--- Testing Intent Query: 'What active projects do we have?' ---")
    response = orchestrator.execute("What active projects do we have?")
    
    print(f"Intent Classification: {response['route']['intent']}")
    print(f"Selected Route: {response['route']['selected']}")
    print(f"Response Status: {response['response']['status']}")
    print(f"Answer Preview: \n{response['response']['answer'][:200]}...")

    print("\n--- Testing Intent Query: 'Show me projects forming now' ---")
    response = orchestrator.execute("Show me projects forming now")
    print(f"Answer Preview: \n{response['response']['answer'][:200]}...")

if __name__ == "__main__":
    test_intent_query()
