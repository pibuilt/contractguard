from sentence_transformers import SentenceTransformer
from typing import List
import numpy as np


class EmbeddingService:
    def __init__(self):
        # Load once (IMPORTANT: do not reload per request)
        self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    def encode(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.array([])

        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=False,
            normalize_embeddings=True  # important for cosine similarity
        )

        return embeddings