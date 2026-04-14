from worker.services.risk_detector import detect_risks
from worker.services.llm_service import llm_service

print(detect_risks(
    "The contract may be terminated without notice at the sole discretion of the company.",
    llm_service=llm_service
))