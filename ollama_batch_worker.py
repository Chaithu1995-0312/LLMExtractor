import json
import requests
import os
import time
import hashlib
from pathlib import Path
from tqdm import tqdm
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_URL = f"{OLLAMA_HOST}/api/generate"
MODEL = os.getenv("LOCAL_LLM_MODEL", "phi3:latest")

SHARD_DIR = "cognitive_shards"
OUT_DIR = "processed_shards"
CHECKPOINT = "checkpoint.txt"

Path(OUT_DIR).mkdir(exist_ok=True)

def load_checkpoint():
    if os.path.exists(CHECKPOINT):
        try:
            return int(open(CHECKPOINT).read().strip())
        except:
            return 0
    return 0

def save_checkpoint(i):
    with open(CHECKPOINT, "w") as f:
        f.write(str(i))

def calculate_accuracy_heuristic(source_text, result_data):
    """
    Reinforced Heuristic-Based Accuracy Detection.
    Accuracy is defined as the ratio of 'Traceable Insights' to 'Total Insights'.
    An insight is traceable if it contains key phrases or named entities from the source.
    """
    if not isinstance(result_data, dict):
        return 0.0
    
    total_insights = 0
    traceable_count = 0
    
    # Check decisions, tasks, and insights
    for key in ["decisions", "tasks", "insights"]:
        items = result_data.get(key, [])
        for item in items:
            total_insights += 1
            item_text = str(item).lower()
            
            # 1. Basic word overlap check (words > 5 chars)
            words = [w for w in item_text.split() if len(w) > 5]
            if not words: 
                continue
            
            # 2. Key phrase check (traceability)
            match_found = any(w in source_text.lower() for w in words)
            if match_found:
                traceable_count += 1
                
    if total_insights == 0:
        # NO_SIGNAL: Return 0.0 to indicate no extraction was possible/performed
        return 0.0 
        
    base_accuracy = traceable_count / total_insights
    
    # 3. Confidence Multiplier based on source density
    # Shards are capped at ~3k tokens. Density penalty for very short or very long inputs.
    source_len = len(source_text)
    density_multiplier = min(1.0, source_len / 2000) 
    
    final_score = round(base_accuracy * density_multiplier, 2)
    return final_score

def process_shard(path):
    start_time = time.perf_counter()
    
    with open(path, "r", encoding="utf-8") as f:
        try:
            raw_text = f.read()
            data = json.loads(raw_text)
            source_text = data.get('text', '')
        except Exception as e:
            print(f"Error reading shard {path}: {e}")
            return None

    # Shard hash for lineage tracking
    shard_hash = hashlib.md5(source_text.encode('utf-8')).hexdigest()

    # Reduce prompt size and emphasize brevity
    prompt = f"""
Summarize core insights from this conversation chunk.
Return JSON ONLY:
{{
"decisions": [],
"tasks": [],
"insights": []
}}
TEXT:
{source_text[:6000]} 
"""

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "num_ctx": 4096,
            "temperature": 0
        }
    }

    max_retries = 2
    ollama_response = None
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            r = requests.post(OLLAMA_URL, json=payload, timeout=60)
            r.raise_for_status()
            ollama_response = r.json()["response"]
            break
        except Exception as e:
            last_error = str(e)
            if attempt < max_retries:
                time.sleep(2)
            else:
                print(f"\nFinal error for {path}: {e}")

    latency_ms = int((time.perf_counter() - start_time) * 1000)

    # Build the final governance-grade structure
    result = {
        "shard_id": path,
        "shard_hash": shard_hash,
        "audit": {
            "model": MODEL,
            "latency_ms": latency_ms,
            "input_chars": len(source_text),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "SUCCESS" if ollama_response else "FAILED",
            "error": last_error
        },
        "ollama_output": None,
        "accuracy_score": 0.0,
        "genai_review": {
            "status": "PENDING",
            "reason": "GENAI_GATEWAY_NOT_TRIGGERED"
        }
    }

    if ollama_response:
        try:
            result_data = json.loads(ollama_response)
            result["ollama_output"] = result_data
            result["accuracy_score"] = calculate_accuracy_heuristic(source_text, result_data)
        except json.JSONDecodeError:
            result["ollama_raw"] = ollama_response
            result["audit"]["status"] = "JSON_DECODE_ERROR"

    return result

def run_batch():
    shards = sorted(Path(SHARD_DIR).glob("*.jsonl"), key=lambda x: int(x.stem.split('_')[1]) if '_' in x.stem else 0)
    start = load_checkpoint()

    print(f"Starting HARDENED cognitive pipeline from shard {start} using model {MODEL}...")

    for i in tqdm(range(start, len(shards))):
        shard_path = shards[i]
        result_payload = process_shard(shard_path)

        if result_payload:
            # Inject actual numeric shard_id for filename consistency
            result_payload["shard_id"] = i
            with open(f"{OUT_DIR}/result_{i}.json", "w", encoding="utf-8") as f:
                json.dump(result_payload, f, indent=2)
            save_checkpoint(i + 1)
        else:
            with open(f"{OUT_DIR}/error_{i}.txt", "w", encoding="utf-8") as f:
                f.write(f"Failed to process shard {i}")
            save_checkpoint(i + 1)

    print("Hardened Batch processing complete. Results saved with full audit trail.")

if __name__ == "__main__":
    run_batch()
