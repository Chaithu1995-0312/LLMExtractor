import os
import numpy as np
from typing import List, Optional
import logging

class VectorEmbedder:
    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VectorEmbedder, cls).__new__(cls)
        return cls._instance

    def _get_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                # Use a lightweight, high-performance model suitable for local use
                # 384 dimensions
                print("Loading embedding model: all-MiniLM-L6-v2 ...")
                self._model = SentenceTransformer('all-MiniLM-L6-v2')
            except ImportError:
                print("Error: sentence-transformers not installed. Please install it.")
                raise
            except Exception as e:
                print(f"Error loading model: {e}")
                raise
        return self._model

    def _rewrite_with_llm(self, original_query: str) -> str:
        """
        Optional GENAI call to expand or refine the query.
        """
        try:
            # Use a sensible default for context_text if not available in this scope
            context_text = "No additional context available for query expansion."
            prompt = f"Context from memory:\n{context_text}\n\nUser: {original_query}\nAssistant:"
            
            # Check for OpenAI Key
            openai_key = os.environ.get("OPENAI_API_KEY")
            if openai_key:
                print(f"DEBUG: OpenAI API Key found. Calling GPT-4o for rewrite...")
                from openai import OpenAI
                client = OpenAI(api_key=openai_key)
                completion = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0
                )
                response_text = completion.choices[0].message.content
                print(f"DEBUG: LLM Rewrote query to: '{response_text}'")
                return response_text
            
            print(f"DEBUG: Rewriting query '{original_query}' (Fallback)...")
            return f"{original_query} including related nexus prompts and brick documentation"
        except Exception as e:
            print(f"LLM Rewrite failed: {e}")
            return original_query # Fallback to original

    def embed_query(self, query: str, use_genai: bool = False) -> np.ndarray:
        """
        Embeds a single query string into a 1x384 vector.
        If use_genai is True, it first modifies the query using an LLM.
        """
        search_text = query
        if use_genai:
            search_text = self._rewrite_with_llm(query)

        model = self._get_model()
        embedding = model.encode([search_text], convert_to_numpy=True)
        return embedding.astype("float32")

    
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """
        Embeds a list of texts into a Nx384 matrix.
        Enforces hard length limits to avoid pathological attention cost.
        """
        if not texts:
            return np.array([], dtype="float32").reshape(0, 384)

        MAX_CHARS = 2000          # hard safety cap
        BATCH_SIZE = 16           # CPU-safe
        SAFE_TEXTS = []

        for t in texts:
            if not t:
                continue
            if len(t) > MAX_CHARS:
                t = t[:MAX_CHARS]
            SAFE_TEXTS.append(t)

        model = self._get_model()

        embeddings = model.encode(
            SAFE_TEXTS,
            convert_to_numpy=True,
            batch_size=BATCH_SIZE,
            show_progress_bar=True
        )

        return embeddings.astype("float32")


# Global singleton accessor
def get_embedder():
    return VectorEmbedder()
