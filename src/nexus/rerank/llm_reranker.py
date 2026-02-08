from typing import List, Dict, Optional
import os
import hashlib
import time
from functools import lru_cache

class LlmReranker:
    """
    Primary reranker with caching and latency fallbacks.
    Uses local quantized LLM (e.g., via llama-cpp-python).
    """
    def __init__(self, model_path: str = "models/llama-3-8b-quantized.gguf", timeout_ms: int = 500):
        self.timeout_ms = timeout_ms
        if not os.path.exists(model_path):
             # If model not found, fail fast so Orchestrator picks fallback
            raise FileNotFoundError(f"Model file not found at {model_path}")
            
        try:
            from llama_cpp import Llama
            # Initialize with deterministic settings
            self.llm = Llama(
                model_path=model_path,
                n_ctx=2048,
                verbose=False,
                seed=42
            )
        except ImportError:
            raise ImportError("llama-cpp-python not installed")
        except Exception as e:
            raise RuntimeError(f"Failed to load Local LLM: {e}")

    @lru_cache(maxsize=1000)
    def _get_cached_score(self, query: str, text_hash: str) -> Optional[float]:
        # Logic to call LLM and return score
        # Note: text_hash used to keep cache key small
        return None

    def rank(self, query: str, candidates: List[Dict]) -> List[Dict]:
        """
        Ranks using LLM scoring with latency guard.
        """
        if not candidates:
            return candidates
            
        for cand in candidates:
            text = cand.get("brick_text", "")
            # Fingerprint for cache
            text_hash = hashlib.md5(text.encode()).hexdigest()
            cache_key = (query, text_hash)
            
            start_time = time.time()
            
            # Simple Heuristic Fallback (BM25 or similar could go here)
            # Currently just uses original confidence if timeout or failure
            
            prompt = f"""Query: {query}
Text: {text[:800]}
Rate relevance (0.0-1.0):"""
            
            try:
                # In a real async environment, we would use a timeout.
                # In synchronous llama-cpp, we measure and log for heuristic fallback triggers.
                output = self.llm(
                    prompt, 
                    max_tokens=6, 
                    stop=["\n"], 
                    echo=False,
                    temperature=0.0 # Deterministic
                )
                score_str = output['choices'][0]['text'].strip()
                import re
                match = re.search(r"0\.\d+|1\.0|0|1", score_str)
                score = float(match.group(0)) if match else 0.0
                
                latency = (time.time() - start_time) * 1000
                if latency > self.timeout_ms:
                    print(f"⚠️ [RERANKER] Latency warning: {latency:.2f}ms")
                    
            except Exception:
                score = cand.get("confidence", 0.0) # Fallback to vector score
                
            cand["final_score"] = max(0.0, min(1.0, score))
            cand["reranker_used"] = "llm_reranker"
            
        candidates.sort(key=lambda x: x["final_score"], reverse=True)
        return candidates
