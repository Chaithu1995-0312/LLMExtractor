from typing import List, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
import re

class L3KeywordExtractor:
    """
    Deterministic keyword extractor using TF-IDF.
    Extracts most representative terms for a cluster of nodes.
    """

    def __init__(self, top_n: int = 5):
        self.top_n = top_n
        self.vectorizer = TfidfVectorizer(
            stop_words='english',
            max_features=1000,
            token_pattern=r'(?u)\b[a-zA-Z]{3,}\b' # only words with 3+ letters
        )

    def extract_keywords(self, cluster_statements: List[str]) -> List[str]:
        """
        Extract top_n keywords from a list of statements.
        """
        if not cluster_statements or len(cluster_statements) == 0:
            return []
        
        # Clean statements: remove special chars, lower case
        clean_statements = [self._clean_text(s) for s in cluster_statements]
        # Filter out empty strings
        clean_statements = [s for s in clean_statements if s.strip()]
        
        if not clean_statements:
            return []

        try:
            tfidf_matrix = self.vectorizer.fit_transform(clean_statements)
            feature_names = self.vectorizer.get_feature_names_out()
            
            # Sum tf-idf scores across all documents in cluster
            sums = tfidf_matrix.sum(axis=0)
            data = []
            for col, term in enumerate(feature_names):
                data.append((term, sums[0, col]))
            
            # Sort by score descending
            ranking = sorted(data, key=lambda x: x[1], reverse=True)
            
            return [term for term, score in ranking[:self.top_n]]
        except Exception:
            # Fallback for very small or low-signal clusters: simple word frequency
            return self._fallback_frequency(clean_statements)

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        text = text.lower()
        text = re.sub(r'[^a-z\s]', '', text)
        return text

    def _fallback_frequency(self, statements: List[str]) -> List[str]:
        words = []
        for s in statements:
            words.extend([w for w in s.split() if len(w) >= 3])
        
        from collections import Counter
        counts = Counter(words)
        # remove common stop words manually if needed, but sklearn does better
        return [word for word, count in counts.most_common(self.top_n)]
