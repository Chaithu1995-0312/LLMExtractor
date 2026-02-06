
import os
import sys

# Ensure src is in path
sys.path.append(os.path.join(os.getcwd(), "src"))

from nexus.vector.embedder import get_embedder

def test_rewrite():
    embedder = get_embedder()
    query = "Nexus architecture"
    
    print(f"Testing rewrite for: '{query}'")
    
    # Test without GENAI (should be original)
    res_no_genai = embedder.embed_query(query, use_genai=False)
    print("Embedded without GENAI.")
    
    # Test with GENAI
    # Note: This will attempt OpenAI call if key is set, or use fallback
    res_with_genai = embedder.embed_query(query, use_genai=True)
    print("Embedded with GENAI (check DEBUG logs above).")

if __name__ == "__main__":
    test_rewrite()
