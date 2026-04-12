import faiss
import numpy as np
from typing import List
import os
import pickle

class VectorStore:
    def __init__(self, dimension: int):
        self.dimension = dimension

        # L2 index (we'll normalize later for cosine)
        self.index = faiss.IndexFlatL2(dimension)

        # mapping: index position → clause_id
        self.id_map = []

    def add(self, embeddings: np.ndarray, ids: List[int]):
        if len(embeddings) != len(ids):
            raise ValueError("Embeddings and IDs must match")

        self.index.add(embeddings)
        self.id_map.extend(ids)

    def search(self, query_embedding: np.ndarray, k: int = 5):
        if query_embedding.ndim == 1:
            query_embedding = np.expand_dims(query_embedding, axis=0)

        distances, indices = self.index.search(query_embedding, k)

        results = []
        for idx in indices[0]:
            if idx == -1:
                continue
            if 0 <= idx < len(self.id_map):
                results.append(self.id_map[idx])

        return results
    
    def save(self, path: str):
        os.makedirs(path, exist_ok=True)

        faiss.write_index(self.index, os.path.join(path, "index.faiss"))

        with open(os.path.join(path, "id_map.pkl"), "wb") as f:
            pickle.dump(self.id_map, f)


    def load(self, path: str):
        index_path = os.path.join(path, "index.faiss")
        map_path = os.path.join(path, "id_map.pkl")

        if os.path.exists(index_path) and os.path.exists(map_path):
            self.index = faiss.read_index(index_path)

            with open(map_path, "rb") as f:
                self.id_map = pickle.load(f)