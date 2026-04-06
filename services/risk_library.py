# services/risk_library.py

RISK_LIBRARY = [
    {
        "risk_type": "Payment Delay",
        "description": "Payment terms are vague or allow excessive delay, impacting cash flow.",
        "severity": "high",
        "keywords": ["delay", "net 60", "net 90", "late payment", "deferred"],
        "embedding_hint": "payment terms that allow delayed or unclear payment obligations"
    },
    {
        "risk_type": "Unilateral Termination",
        "description": "One party can terminate the contract without notice or cause.",
        "severity": "high",
        "keywords": ["terminate at will", "without notice", "sole discretion"],
        "embedding_hint": "termination clause allowing one party to end contract unfairly"
    },
    {
        "risk_type": "Liability Limitation",
        "description": "Limits liability in a way that may expose your organization to risk.",
        "severity": "medium",
        "keywords": ["limited liability", "no liability", "cap on damages"],
        "embedding_hint": "clause limiting legal or financial responsibility"
    },
    {
        "risk_type": "Auto Renewal",
        "description": "Contract renews automatically without explicit consent.",
        "severity": "medium",
        "keywords": ["auto-renew", "automatic renewal", "renew unless terminated"],
        "embedding_hint": "contract automatically renewing without explicit approval"
    },
    {
        "risk_type": "Ambiguous Scope",
        "description": "Scope of work is unclear or loosely defined.",
        "severity": "low",
        "keywords": ["as needed", "as applicable", "reasonable efforts"],
        "embedding_hint": "unclear or vague scope of responsibilities"
    },
]