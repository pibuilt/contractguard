from worker.services.risk_library import RISK_LIBRARY


def normalize(text: str) -> str:
    return text.lower().strip()


# IMPROVED: fuzzy + partial matching
def find_risk_in_library(risk_type: str):
    target = normalize(risk_type)

    for risk in RISK_LIBRARY:
        lib_type = normalize(risk["risk_type"])

        # exact match
        if lib_type == target:
            return risk

        # partial match (important)
        if target in lib_type or lib_type in target:
            return risk

    return None


def detect_risks(clause_text: str, llm_service=None):
    if not clause_text or not clause_text.strip():
        return []

    clause_norm = normalize(clause_text)
    results = []

    # -------------------------------
    # RULE-BASED DETECTION
    # -------------------------------
    for risk in RISK_LIBRARY:
        matched_keywords = [
            kw for kw in risk["keywords"]
            if normalize(kw) in clause_norm
        ]

        if matched_keywords:
            confidence = min(0.6 + 0.1 * len(matched_keywords), 0.95)

            results.append({
                "risk_type": risk["risk_type"],
                "severity": risk["severity"],
                "confidence": round(confidence, 3),
                "source": "rule"
            })

    # -------------------------------
    # LLM FALLBACK
    # -------------------------------
    if not results and llm_service:
        llm_result = llm_service.analyze_clause(clause_text)

        # FIX: never return empty
        if not llm_result:
            return [{
                "risk_type": "Unknown",
                "severity": "low",
                "confidence": 0.3,
                "source": "fallback",
                "note": "LLM returned empty response"
            }]

        if llm_result["confidence"] < 0.7:
            return results

        # FIX: map to library (canonical)
        lib_match = find_risk_in_library(llm_result["risk_type"])

        if lib_match:
            risk_type = lib_match["risk_type"]
            severity = lib_match["severity"]
        else:
            risk_type = llm_result["risk_type"]
            severity = "medium"

        results.append({
            "risk_type": risk_type,
            "severity": severity,
            "confidence": llm_result["confidence"],
            "source": "llm",
            "llm_data": llm_result
        })

    return results