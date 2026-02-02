from typing import List, Dict
import os

class LlmReranker:
    """
    Primary reranker.
    Uses local quantized LLM (e.g., via llama-cpp-python).
    """
    def __init__(self, model_path: str = "models/llama-3-8b-quantized.gguf"):
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

    def rank(self, query: str, candidates: List[Dict]) -> List[Dict]:
        """
        Ranks using LLM scoring.
        """
        if not candidates:
            return candidates
            
        for cand in candidates:
            text = cand.get("brick_text", "")
            # Truncate text to avoid context overflow
            prompt = f"""Query: {query}
Text: {text[:800]}
Rate relevance (0.0-1.0):"""
            
            try:
                output = self.llm(
                    prompt, 
                    max_tokens=6, 
                    stop=["\n"], 
                    echo=False,
                    temperature=0.0 # Deterministic
                )
                score_str = output['choices'][0]['text'].strip()
                # Parse float, handle potential extra chars
                import re
                match = re.search(r"0\.\d+|1\.0|0|1", score_str)
                if match:
                    score = float(match.group(0))
                else:
                    score = 0.0
            except Exception:
                score = 0.0
                
            cand["final_score"] = max(0.0, min(1.0, score))
            cand["reranker_used"] = "llm_reranker"
            
        candidates.sort(key=lambda x: x["final_score"], reverse=True)
        return candidates
