import numpy as np
from services.risk_library import RISK_LIBRARY
from services.embedding_instance import embedding_service

# Precompute risk embeddings ONCE
RISK_HINT_EMBEDDINGS = embedding_service.encode(
    [r["embedding_hint"] for r in RISK_LIBRARY]
)


def keyword_match_score(clause_text: str, keywords: list[str]) -> float:
    clause_lower = clause_text.lower()
    matches = sum(1 for kw in keywords if kw in clause_lower)
    return matches / len(keywords) if keywords else 0.0


def detect_risks(clause_text: str):
    if not clause_text or not clause_text.strip():
        return []
    
    results = []

    clause_embedding = embedding_service.encode([clause_text])[0]

    for i, risk in enumerate(RISK_LIBRARY):
        kw_score = keyword_match_score(clause_text, risk["keywords"])
        emb_score = float(np.dot(clause_embedding, RISK_HINT_EMBEDDINGS[i]))

        final_score = 0.6 * emb_score + 0.4 * kw_score

        if final_score > 0.4:
            results.append({
                "risk_type": risk["risk_type"],
                "severity": risk["severity"],
                "confidence": round(final_score, 3),
                "description": risk["description"]
            })

    return results