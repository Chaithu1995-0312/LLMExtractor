import os
import sys
import time
import json
import statistics

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from nexus.sync.llm import LLMClient

# Standard Extraction Prompt from test_llm_connectivity.py
SYSTEM_PROMPT = """You are a Deterministic Data Extraction Engine.
You are NOT a chat assistant. You are a compiler component.

Your Goal: Scan the provided Source JSON and identify text segments that belong to the requested Topic IDs.
Your Output: A raw JSON array of "Pointer Objects."

---

### INPUT DATA
1. "Topics": A list of Topic IDs and their descriptions.
2. "Source_JSON": A raw JSON transcript. Nodes may contain:
   - "content": A plain-text fallback string.
   - "content_blocks": Structured blocks (text, code, tool_output). PREFER these for precise extraction.
   - "metadata": Contextual info (content_type, recipient, model).

---

### CRITICAL RULES (VIOLATION = SYSTEM FAILURE)
1. NO PARAPHRASING: You must return the text EXACTLY as it appears in the source.
2. NO MERGING: If information is split across nodes, output separate Pointer Objects.
3. PREFER STRUCTURE: If a fact is found in a `content_blocks` node (e.g., a code snippet or tool result), use the path to that specific block.
4. NO INTERPRETATION: Do not infer facts. Only extract explicit statements.

---

### OUTPUT SCHEMA
Return a JSON Object with a single key "extracted_pointers" containing a list:

{
  "extracted_pointers": [
    {
      "topic_id": "string (must match one of the Input Topics)",
      "json_path": "string (RFC 9535 standard path, e.g., $.messages[3].content_blocks[0].value)",
      "verbatim_quote": "string (exact copy-paste of the text found at that path)"
    }
  ]
}"""

USER_PROMPT = """
TARGET TOPIC: "nexus-server-sync"

DEFINITION:
Technical constraints, architectural decisions, and data flow rules for the Nexus Server Sync system.

SOURCE JSON TO SCAN:
[{"message_id": "bbb21afd-ee2d-4bf0-a37f-edb768ee1084", "role": "user", "content": "The nexus server sync should use a local database for caching metadata before pushing to the cloud.", "model_name": "unknown", "created_at": "2026-01-31T21:47:15.243296+00:00"}]
"""

def benchmark_model(model_name, iterations=3):
    print(f"\n--- Benchmarking Model: {model_name} ---")
    os.environ["LOCAL_LLM_MODEL"] = model_name
    os.environ["LOCAL_LLM_PROVIDER"] = "ollama"
    os.environ["LOCAL_LLM_ENABLED"] = "true"
    os.environ["LLM_STRICT_MODE"] = "true" # Force failure if Ollama is down
    
    client = LLMClient()
    
    latencies = []
    successes = 0
    
    # Warm-up
    print("Warm-up call...")
    try:
        client.generate("Hello", "Hi")
    except Exception as e:
        print(f"Warm-up failed: {e}")
        return None

    for i in range(iterations):
        print(f"Iteration {i+1}/{iterations}...", end="", flush=True)
        start_time = time.time()
        try:
            response = client.generate(SYSTEM_PROMPT, USER_PROMPT)
            end_time = time.time()
            latency = end_time - start_time
            latencies.append(latency)
            
            # Basic validation
            data = json.loads(response)
            if "extracted_pointers" in data:
                successes += 1
                print(f" Success ({latency:.2f}s)")
            else:
                print(f" Failed (Invalid Schema)")
        except Exception as e:
            print(f" Failed ({e})")
    
    if not latencies:
        return None

    results = {
        "model": model_name,
        "avg_latency": statistics.mean(latencies),
        "min_latency": min(latencies),
        "max_latency": max(latencies),
        "success_rate": (successes / iterations) * 100
    }
    return results

def main():
    models_to_test = ["mistral:latest", "llama3:latest", "phi3:latest"]
    all_results = []

    for model in models_to_test:
        res = benchmark_model(model)
        if res:
            all_results.append(res)

    print("\n" + "="*50)
    print(f"{'Model':<20} | {'Avg Latency':<12} | {'Success Rate':<12}")
    print("-" * 50)
    for res in all_results:
        print(f"{res['model']:<20} | {res['avg_latency']:<12.2f}s | {res['success_rate']:<12.1f}%")
    print("="*50)

if __name__ == "__main__":
    main()
