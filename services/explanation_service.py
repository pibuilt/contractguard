def generate_explanation(risk_type: str) -> str:
    explanations = {
        "Unilateral Termination": (
            "This clause allows one party to terminate the agreement without requiring consent "
            "from the other party, which creates an imbalance and increases legal risk."
        ),
        "Auto Renewal": (
            "This clause automatically renews the contract unless explicitly terminated, "
            "which may lead to unintended obligations if not carefully monitored."
        ),
        "Liability Limitation": (
            "This clause limits one party’s liability, potentially exposing the other party "
            "to higher financial or legal risk in case of disputes."
        ),
    }

    return explanations.get(
        risk_type,
        "This clause may introduce potential legal or financial risk and should be reviewed carefully."
    )