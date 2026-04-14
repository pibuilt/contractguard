from worker.services.risk_library import RISK_LIBRARY


def keyword_match_score(clause_text: str, keywords: list[str]) -> float:
    clause_lower = clause_text.lower()
    matches = sum(1 for kw in keywords if kw in clause_lower)
    return matches / len(keywords) if keywords else 0.0

THRESHOLD = 0.5

def detect_risks(clause_text: str, llm_service=None):
    if not clause_text or not clause_text.strip():
        return []

    results = []

    for risk in RISK_LIBRARY:
        kw_score = keyword_match_score(clause_text, risk["keywords"])

        if kw_score >= THRESHOLD:
            results.append({
                "risk_type": risk["risk_type"],
                "severity": risk["severity"],
                "confidence": round(kw_score, 3),
                "source": "rule"
            })

    # -------------------------------
    # LLM fallback (NEW)
    # -------------------------------
    if not results and llm_service:
        llm_result = llm_service.analyze_clause(clause_text)

        if llm_result["confidence"] > 0.4:
            results.append({
                "risk_type": llm_result["risk_type"],
                "severity": "medium",
                "confidence": llm_result["confidence"],
                "source": "llm",
                "llm_data": llm_result
            })

    return results