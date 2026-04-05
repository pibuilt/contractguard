from services.embedding_service import EmbeddingService
from services.vector_instance import vector_store

embedding_service = EmbeddingService()

print("Vector size:", len(vector_store.id_map))

query = "payment terms"
query_embedding = embedding_service.encode([query])[0]

results = vector_store.search(query_embedding, k=3)

print("Results:", results)