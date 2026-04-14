from worker.services.risk_detector import detect_risks
from worker.services.llm_service import llm_service

print(detect_risks(
    "One party can terminate the contract without notice or cause.",
    llm_service=llm_service
))