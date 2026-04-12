from worker.services.risk_library import RISK_LIBRARY


def keyword_match_score(clause_text: str, keywords: list[str]) -> float:
    clause_lower = clause_text.lower()
    matches = sum(1 for kw in keywords if kw in clause_lower)
    return matches / len(keywords) if keywords else 0.0


def detect_risks(clause_text: str):
    if not clause_text or not clause_text.strip():
        return []

    results = []

    for risk in RISK_LIBRARY:
        kw_score = keyword_match_score(clause_text, risk["keywords"])

        final_score = kw_score

        if final_score > 0.3:  # slightly lower threshold
            results.append({
                "risk_type": risk["risk_type"],
                "severity": risk["severity"],
                "confidence": round(final_score, 3),
                "description": risk["description"]
            })

    return results