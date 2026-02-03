import sys
import os

# Ensure src is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from nexus.cognition import assemble_topic

def main():
    if len(sys.argv) > 1:
        query = sys.argv[1]
    else:
        query = "test topic"
    
    print(f"Running assemble_topic for query: '{query}'")
    try:
        artifact_path = assemble_topic(query)
        print(f"Success! Artifact saved at: {artifact_path}")
        
        # Verify content
        import json
        with open(artifact_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            print("Artifact keys:", data.keys())
            payload = data.get("payload", {})
            print("Payload keys:", payload.keys())
            print(f"Number of documents: {len(payload.get('raw_excerpts', []))}")
            print("Provenance:", payload.get("provenance"))
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
