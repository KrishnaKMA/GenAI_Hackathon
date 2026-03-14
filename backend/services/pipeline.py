def mock_model_output():
    return {
        "fraud_rings_detected": 1,
        "rings": [
            {
                "ring_id": "ring_001",
                "fraud_score": 87,
                "entities": [
                    {"type": "claimant", "name": "John Doe"},
                    {"type": "repair_shop", "name": "AutoFix Toronto"},
                    {"type": "doctor", "name": "Dr. Smith"}
                ],
                "claims": [
                    {"claim_id": "C101", "amount": 4800},
                    {"claim_id": "C102", "amount": 5100},
                    {"claim_id": "C103", "amount": 4950}
                ],
                "risk_factors": [
                    "repair shop appears in multiple claims",
                    "repair costs significantly above average",
                    "shared provider across claimants"
                ]
            }
        ]
    }