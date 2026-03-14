"""
+==========================================================+
|         IBM WATSONX INTERFACE -- TEAMMATE B               |
|                                                          |
|  Hi! This is the ONLY file you need to edit.             |
|                                                          |
|  STEP 1: Fill in these vars in the .env file:            |
|    WATSONX_API_KEY=      (from IBM Cloud -> IAM)          |
|    WATSONX_PROJECT_ID=   (from watsonx.ai project)       |
|    WATSONX_URL=https://us-south.ml.cloud.ibm.com         |
|    DB2_DSN=              (from IBM Cloud -> Db2 service)  |
|                                                          |
|  STEP 2: Fill in the 3 functions marked                  |
|    # TEAMMATE B: YOUR CODE GOES HERE                     |
|                                                          |
|  STEP 3: Test it:                                        |
|    curl http://localhost:8000/factsheets                  |
|    Should return real IBM entries, not mock ones         |
|    Logs should say: [IBM] Using REAL watsonx             |
|                                                          |
|  STEP 4: Test Granite narrative:                         |
|    curl -X POST http://localhost:8000/analyze/any_token  |
|    Report narrative should be AI-generated, not hardcoded|
|                                                          |
|  DO NOT touch any other file. Krishna handles the rest.  |
+==========================================================+
"""

import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from models.schemas import FraudAnalysisResult, FactsheetEntry

# ─────────────────────────────────────────────────────────
# AUTO-DETECTION: switches between mock and real automatically
# When WATSONX_API_KEY is in .env -> real IBM calls run
# When missing -> mock runs (stores locally in JSON file)
# ─────────────────────────────────────────────────────────
WATSONX_API_KEY    = os.getenv("WATSONX_API_KEY")
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID")
WATSONX_URL        = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
DB2_DSN            = os.getenv("DB2_DSN")
USE_MOCK           = not bool(WATSONX_API_KEY)

# Local fallback storage when IBM not connected yet
LOCAL_FACTSHEETS_PATH = Path("data/local_factsheets.json")
LOCAL_FACTSHEETS_PATH.parent.mkdir(exist_ok=True)

if USE_MOCK:
    print("[IBM] WARNING:  WATSONX_API_KEY not found -- using MOCK IBM services")
    print("[IBM] Factsheets stored locally at:", LOCAL_FACTSHEETS_PATH)
else:
    print("[IBM] OK: IBM credentials found -- using REAL watsonx services")


# ─────────────────────────────────────────────────────────
# # TEAMMATE B: INITIALIZE WATSONX CLIENT HERE
# Only runs when credentials are present
# ─────────────────────────────────────────────────────────
watsonx_client = None  # # TEAMMATE B: initialize your client here

if not USE_MOCK:
    pass
    # # TEAMMATE B: YOUR CLIENT INITIALIZATION GOES HERE
    # Example:
    # from ibm_watsonx_ai import APIClient, Credentials
    # credentials = Credentials(url=WATSONX_URL, api_key=WATSONX_API_KEY)
    # watsonx_client = APIClient(credentials)
    # watsonx_client.set.default_project(WATSONX_PROJECT_ID)


# ─────────────────────────────────────────────────────────
# FUNCTION 1 -- Granite narrative generation
# Called by: services/report_generator.py
# Input:  FraudAnalysisResult (scores + evidence)
# Output: 3-paragraph plain English investigator report string
# ─────────────────────────────────────────────────────────
async def generate_narrative(analysis: FraudAnalysisResult) -> str:
    if USE_MOCK:
        return _mock_narrative(analysis)
    else:
        return await _real_narrative(analysis)


# # TEAMMATE B: IMPLEMENT THIS -- calls Granite on watsonx.ai
async def _real_narrative(analysis: FraudAnalysisResult) -> str:
    # # TEAMMATE B: YOUR GRANITE API CALL GOES HERE
    # The prompt to send:
    prompt = f"""You are an insurance fraud investigator writing a formal case report.
Based on the following analysis, write a 3-paragraph investigator summary.

FRAUD SCORES:
- Graph anomaly score: {analysis.gnn_score}/100
- Statistical anomaly score: {analysis.isolation_score}/100
- Combined risk score: {analysis.combined_score}/100
- Risk level: {analysis.risk_level}

KEY EVIDENCE:
{chr(10).join(f'- {e.human_label}' for e in analysis.gnn_evidence)}

KEY ANOMALIES:
{chr(10).join(f'- {f.feature_name}: {f.value} ({f.direction})' for f in analysis.shap_features)}

Write paragraph 1: Summary of fraud indicators found.
Write paragraph 2: Specific patterns and their significance.
Write paragraph 3: Recommended next steps for the investigator.
Use professional tone. Do not include any names or personal data."""

    # Example call pattern (adjust to your exact watsonx SDK version):
    # response = watsonx_client.text.generation.create(
    #     model_id="ibm/granite-13b-instruct-v2",
    #     input=prompt,
    #     parameters={"max_new_tokens": 500, "temperature": 0.3}
    # )
    # return response.get_result()["results"][0]["generated_text"]
    raise NotImplementedError("Teammate B: implement _real_narrative()")


# Mock narrative -- realistic enough for demo without IBM
def _mock_narrative(analysis: FraudAnalysisResult) -> str:
    risk = analysis.risk_level
    score = analysis.combined_score
    top_evidence = analysis.gnn_evidence[0].human_label if analysis.gnn_evidence else "multiple anomalies"

    if risk == "CRITICAL":
        return f"""This claim has been flagged as CRITICAL with a combined fraud score of {score}/100. \
Graph analysis identified a coordinated fraud ring involving {len(analysis.graph_nodes)} entities. \
The primary indicator is that {top_evidence}, a pattern consistent with organized insurance fraud.

The network topology reveals deliberate routing of claims through a single unregistered repair facility, \
with multiple claimants submitting independent claims that share providers, repair shops, and in some cases \
incident witnesses. Statistical analysis confirms that claim amounts, filing velocity, and injury descriptions \
deviate significantly from legitimate claim distributions for this policy type.

Immediate referral to the Special Investigations Unit is recommended. Priority actions include: verifying \
business registration status of all flagged entities, obtaining independent medical examinations for all \
injury claims, issuing preservation notices for surveillance footage at the repair facility, and cross-referencing \
claimant identities against prior fraud databases. Do not settle any linked claims pending investigation."""
    elif risk == "HIGH":
        return f"""This claim has been assigned a HIGH risk score of {score}/100 based on statistical \
anomaly detection. The claimant's filing history shows unusual patterns including {top_evidence}. \
While no organized ring has been detected, individual claim characteristics deviate from expected norms.

Analysis of claim timing, amount distribution, and provider selection suggests possible opportunistic \
fraud. The claim amount ratio relative to policy limits, combined with the filing velocity, places this \
claim in the top 8% of anomalous submissions in our detection system.

Recommend enhanced manual review before processing. An independent assessment of damages is advised, \
along with verification of the incident report against police and third-party records."""
    else:
        return f"""This claim presents a LOW risk profile with a combined score of {score}/100. \
Standard claim characteristics are within expected parameters for this policy type and claim category. \
No suspicious network connections were identified in the entity graph.

Statistical features including claim amount, filing timing, and provider selection all fall within \
normal distributions for comparable claims. The claimant's history shows no prior anomalies.

Standard processing is recommended. No additional investigation required at this time."""


# ─────────────────────────────────────────────────────────
# FUNCTION 2 -- log inference to IBM governance
# Called by: api/routes/analysis.py after every analysis
# Input:  claim_token string + FraudAnalysisResult
# Output: factsheet_id string (UUID)
# ─────────────────────────────────────────────────────────
async def log_factsheet(claim_token: str, analysis: FraudAnalysisResult, adjuster_id: str) -> str:
    if USE_MOCK:
        return _mock_log_factsheet(claim_token, analysis, adjuster_id)
    else:
        return await _real_log_factsheet(claim_token, analysis, adjuster_id)


# # TEAMMATE B: IMPLEMENT THIS -- logs to watsonx.governance
async def _real_log_factsheet(claim_token: str, analysis: FraudAnalysisResult, adjuster_id: str) -> str:
    # # TEAMMATE B: YOUR GOVERNANCE FACTSHEET LOGGING GOES HERE
    # The data to log:
    factsheet_data = {
        "claim_token":    claim_token,
        "model_version":  "graphsage-v1.0",
        "combined_score": analysis.combined_score,
        "risk_level":     analysis.risk_level,
        "adjuster_id":    adjuster_id,
        "decision":       "FLAGGED" if analysis.combined_score >= 60 else "APPROVED",
        "timestamp":      datetime.utcnow().isoformat(),
    }
    # Example:
    # response = watsonx_client.factsheets.store(factsheet_data)
    # return response["factsheet_id"]
    raise NotImplementedError("Teammate B: implement _real_log_factsheet()")


# Mock -- stores to local JSON file so FactsheetPanel works
def _mock_log_factsheet(claim_token: str, analysis: FraudAnalysisResult, adjuster_id: str) -> str:
    factsheet_id = str(uuid.uuid4())[:8].upper()
    entry = {
        "factsheet_id":  factsheet_id,
        "claim_token":   claim_token,
        "timestamp":     datetime.utcnow().isoformat(),
        "model_version": "graphsage-v1.0-mock",
        "combined_score": analysis.combined_score,
        "risk_level":    analysis.risk_level,
        "adjuster_id":   adjuster_id,
        "decision":      "FLAGGED" if analysis.combined_score >= 60 else "APPROVED",
    }
    # Load existing, append, save
    existing = []
    if LOCAL_FACTSHEETS_PATH.exists():
        with open(LOCAL_FACTSHEETS_PATH) as f:
            existing = json.load(f)
    existing.insert(0, entry)
    existing = existing[:50]  # keep last 50
    with open(LOCAL_FACTSHEETS_PATH, "w") as f:
        json.dump(existing, f, indent=2)
    return factsheet_id


# ─────────────────────────────────────────────────────────
# FUNCTION 3 -- get governance logs for FactsheetPanel
# Called by: api/routes/claims.py GET /factsheets
# Output: list of FactsheetEntry
# ─────────────────────────────────────────────────────────
async def get_factsheets(limit: int = 10) -> list[FactsheetEntry]:
    if USE_MOCK:
        return _mock_get_factsheets(limit)
    else:
        return await _real_get_factsheets(limit)


# # TEAMMATE B: IMPLEMENT THIS -- fetches from watsonx.governance
async def _real_get_factsheets(limit: int) -> list[FactsheetEntry]:
    # # TEAMMATE B: YOUR GOVERNANCE FETCH GOES HERE
    # Example:
    # response = watsonx_client.factsheets.list(limit=limit)
    # return [FactsheetEntry(**entry) for entry in response["resources"]]
    raise NotImplementedError("Teammate B: implement _real_get_factsheets()")


# Mock -- reads from local JSON file
def _mock_get_factsheets(limit: int) -> list[FactsheetEntry]:
    if not LOCAL_FACTSHEETS_PATH.exists():
        return _seed_mock_factsheets()
    with open(LOCAL_FACTSHEETS_PATH) as f:
        data = json.load(f)
    return [FactsheetEntry(**entry) for entry in data[:limit]]


def _seed_mock_factsheets() -> list[FactsheetEntry]:
    """Returns hardcoded entries so FactsheetPanel is never empty"""
    entries = [
        {"factsheet_id": "A1B2C3D4", "claim_token": "CLAIM_001", "timestamp": "2024-06-15T09:23:11",
         "model_version": "graphsage-v1.0-mock", "combined_score": 91.0,
         "risk_level": "CRITICAL", "adjuster_id": "adj_001", "decision": "FLAGGED"},
        {"factsheet_id": "E5F6G7H8", "claim_token": "CLAIM_002", "timestamp": "2024-06-15T10:11:44",
         "model_version": "graphsage-v1.0-mock", "combined_score": 12.0,
         "risk_level": "LOW", "adjuster_id": "adj_002", "decision": "APPROVED"},
        {"factsheet_id": "I9J0K1L2", "claim_token": "CLAIM_003", "timestamp": "2024-06-15T11:05:02",
         "model_version": "graphsage-v1.0-mock", "combined_score": 68.0,
         "risk_level": "HIGH", "adjuster_id": "adj_001", "decision": "FLAGGED"},
    ]
    return [FactsheetEntry(**e) for e in entries]
