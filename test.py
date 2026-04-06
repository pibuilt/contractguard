from services.risk_detector import detect_risks

clause = "The payment shall be made within 90 days of invoice."

print(detect_risks(clause))