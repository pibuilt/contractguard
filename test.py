from worker.services.risk_detector import detect_risks
from worker.services.llm_service import llm_service


clauses = [
    # Payment Delay
    "Payment shall be made within 90 days of invoice submission.",

    # Unilateral Termination
    "The company may terminate this agreement at its sole discretion without notice.",

    # Liability Limitation
    "The vendor shall have no liability for any damages arising from this agreement.",

    # Auto Renewal
    "This agreement will automatically renew unless terminated by either party.",

    # Ambiguous Scope
    "Services will be provided as needed and as applicable.",

    # Multi-risk clause
    """Payment shall be made within 90 days.
    The agreement may be terminated without notice.""",

    # LLM fallback case
    "The agreement can be ended by one party at any time without justification."
]


for i, clause in enumerate(clauses, 1):
    print("\n" + "="*60)
    print(f"CLAUSE {i}:")
    print(clause.strip())

    risks = detect_risks(clause, llm_service=llm_service)

    print("\nDETECTED RISKS:")
    for r in risks:
        print(r)