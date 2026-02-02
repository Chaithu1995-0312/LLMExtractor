# src/nexus/vector/index.py

from .local_index import LocalVectorIndex

# Public, stable API
VectorIndex = LocalVectorIndex

__all__ = ["VectorIndex"]
