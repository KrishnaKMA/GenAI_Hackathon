"""
+==========================================================+
|         IBM WATSONX INTERFACE -- TEAMMATE B               |
|                                                          |
|  STEP 1: Fill in these vars in the .env file:            |
|    WATSONX_API_KEY=      (from IBM Cloud -> IAM)          |
|    WATSONX_PROJECT_ID=   (from watsonx.ai project)       |
|    WATSONX_URL=https://us-south.ml.cloud.ibm.com         |
|    DB2_DSN=              (from IBM Cloud -> Db2 service)  |
|    WATSONX_SPACE_ID=     (from watsonx.ai -> Spaces)      |
|                                                          |
|  STEP 2: Test Granite narrative:                         |
|    curl -X POST http://localhost:8000/analyze/any_token  |
|    Logs should say: [IBM] OK: IBM credentials found      |
|    Narrative in response should be AI-generated          |
|                                                          |
|  STEP 3: Test factsheets:                                |
|    curl http://localhost:8000/factsheets                  |
|    Should return real watsonx.governance entries         |
+==========================================================+
"""

import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from models.schemas import FraudAnalysisResult, FactsheetEntry
import asyncio

from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
from ibm_aigov_facts_client import AIGovFactsClient



# AUTO-DETECTION
# Real IBM calls run when WATSONX_API_KEY is present.
# Falls back to local JSON mock when credentials are missing.

WATSONX_API_KEY    = os.getenv("WATSONX_API_KEY")
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID")
WATSONX_SPACE_ID   = os.getenv("WATSONX_SPACE_ID")   # needed for governance
WATSONX_URL        = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
DB2_DSN            = os.getenv("DB2_DSN")
USE_MOCK           = not bool(WATSONX_API_KEY)

LOCAL_FACTSHEETS_PATH = Path("data/local_factsheets.json")
LOCAL_FACTSHEETS_PATH.parent.mkdir(exist_ok=True)

if USE_MOCK:
    print("[IBM] WARNING: WATSONX_API_KEY not found -- using MOCK IBM services")
    print("[IBM] Factsheets stored locally at:", LOCAL_FACTSHEETS_PATH)
else:
    print("[IBM] OK: IBM credentials found -- using REAL watsonx services")


# CLIENT INITIALIZATION (only when credentials present)
watsonx_client = None
granite_model  = None
facts_client   = None  # watsonx.governance client

if not USE_MOCK:
    # Watsonx AI client (for Granite)
    credentials = Credentials(
        url=WATSONX_URL,
        api_key=WATSONX_API_KEY,
    )
    watsonx_client = APIClient(credentials)

    # Granite LLM
    granite_model = ModelInference(
        model_id="ibm/granite-3-8b-instruct",
        api_client=watsonx_client,
        project_id=WATSONX_PROJECT_ID,
        params={
            GenParams.MAX_NEW_TOKENS:     450,
            GenParams.MIN_NEW_TOKENS:     80,
            GenParams.TEMPERATURE:        0.2,
            GenParams.TOP_P:              0.9,
            GenParams.REPETITION_PENALTY: 1.05,
        },
        verify=False,
    )

    # watsonx.governance facts client
    # Prefers WATSONX_SPACE_ID, falls back to project
    if WATSONX_SPACE_ID:
        facts_client = AIGovFactsClient(
            api_key=WATSONX_API_KEY,
            experiment_name="claimshield-fraud-detection",
            container_type="space",
            container_id=WATSONX_SPACE_ID,
            set_as_current_experiment=True,
        )
        print("[IBM] OK: watsonx.governance connected via space")
    elif WATSONX_PROJECT_ID:
        facts_client = AIGovFactsClient(
            api_key=WATSONX_API_KEY,
            experiment_name="claimshield-fraud-detection",
            container_type="project",
            container_id=WATSONX_PROJECT_ID,
            set_as_current_experiment=True,
        )
        print("[IBM] OK: watsonx.governance connected via project")
    else:
        print("[IBM] WARNING: No WATSONX_SPACE_ID or WATSONX_PROJECT_ID -- governance disabled")



# FUNCTION 1 — Granite narrative generation
# Called by: services/report_generator.py
# Input:  FraudAnalysisResult (scores + evidence)
# Output: 3-paragraph plain English investigator report string
async def generate_narrative(analysis: FraudAnalysisResult) -> str:
    if USE_MOCK:
        return _mock_narrative(analysis)
    return await _real_narrative(analysis)


async def _real_narrative(analysis: FraudAnalysisResult) -> str:
    if granite_model is None:
        raise RuntimeError("[IBM] Granite model is not initialized -- check WATSONX_API_KEY and WATSONX_PROJECT_ID")

    prompt = f"""You are an insurance fraud investigator writing a formal case report.
Based on the following analysis, write a 3-paragraph investigator summary.

FRAUD SCORES:
- Graph anomaly score: {analysis.gnn_score}/100
- Statistical anomaly score: {analysis.isolation_score}/100
- Combined risk score: {analysis.combined_score}/100
- Risk level: {analysis.risk_level}

KEY EVIDENCE:
{chr(10).join(f'- {e.human_label}' for e in analysis.gnn_evidence) if analysis.gnn_evidence else '- No graph evidence provided'}

KEY ANOMALIES:
{chr(10).join(f'- {f.feature_name}: {f.value} ({f.direction})' for f in analysis.shap_features) if analysis.shap_features else '- No tabular anomalies provided'}

Write paragraph 1: Summary of fraud indicators found.
Write paragraph 2: Specific patterns and their significance.
Write paragraph 3: Recommended next steps for the investigator.
Use professional tone. Do not include any names or personal data."""

    def _call_model():
        text = granite_model.generate_text(prompt=prompt)
        return text.strip() if isinstance(text, str) else str(text)

    return await asyncio.to_thread(_call_model)


def _mock_narrative(analysis: FraudAnalysisResult) -> str:
    risk  = analysis.risk_level
    score = analysis.combined_score
    top_evidence = analysis.gnn_evidence[0].human_label if analysis.gnn_evidence else "multiple anomalies"

    if risk == "CRITICAL":
        return (
            f"This claim has been flagged as CRITICAL with a combined fraud score of {score}/100. "
            f"Graph analysis identified a coordinated fraud ring involving {len(analysis.graph_nodes)} entities. "
            f"The primary indicator is that {top_evidence}, a pattern consistent with organized insurance fraud.\n\n"
            "The network topology reveals deliberate routing of claims through a single unregistered repair facility, "
            "with multiple claimants submitting independent claims that share providers, repair shops, and in some cases "
            "incident witnesses. Statistical analysis confirms that claim amounts, filing velocity, and injury descriptions "
            "deviate significantly from legitimate claim distributions for this policy type.\n\n"
            "Immediate referral to the Special Investigations Unit is recommended. Priority actions include: verifying "
            "business registration status of all flagged entities, obtaining independent medical examinations for all "
            "injury claims, issuing preservation notices for surveillance footage at the repair facility, and cross-referencing "
            "claimant identities against prior fraud databases. Do not settle any linked claims pending investigation."
        )
    elif risk == "HIGH":
        return (
            f"This claim has been assigned a HIGH risk score of {score}/100 based on statistical anomaly detection. "
            f"The claimant's filing history shows unusual patterns including {top_evidence}. "
            "While no organized ring has been detected, individual claim characteristics deviate from expected norms.\n\n"
            "Analysis of claim timing, amount distribution, and provider selection suggests possible opportunistic fraud. "
            "The claim amount ratio relative to policy limits, combined with the filing velocity, places this claim in "
            "the top 8% of anomalous submissions in our detection system.\n\n"
            "Recommend enhanced manual review before processing. An independent assessment of damages is advised, "
            "along with verification of the incident report against police and third-party records."
        )
    else:
        return (
            f"This claim presents a LOW risk profile with a combined score of {score}/100. "
            "Standard claim characteristics are within expected parameters for this policy type and claim category. "
            "No suspicious network connections were identified in the entity graph.\n\n"
            "Statistical features including claim amount, filing timing, and provider selection all fall within "
            "normal distributions for comparable claims. The claimant's history shows no prior anomalies.\n\n"
            "Standard processing is recommended. No additional investigation required at this time."
        )



# FUNCTION 2 — Log factsheet to watsonx.governance
# Called by: api/routes/analysis.py after every analysis
# Input:  claim_token + FraudAnalysisResult + adjuster_id
# Output: factsheet_id string
async def log_factsheet(claim_token: str, analysis: FraudAnalysisResult, adjuster_id: str) -> str:
    if USE_MOCK:
        return _mock_log_factsheet(claim_token, analysis, adjuster_id)
    return await _real_log_factsheet(claim_token, analysis, adjuster_id)


async def _real_log_factsheet(claim_token: str, analysis: FraudAnalysisResult, adjuster_id: str) -> str:
    factsheet_id = str(uuid.uuid4())[:8].upper()
    decision     = "FLAGGED" if analysis.combined_score >= 60 else "APPROVED"

    if facts_client is None:
        print("[IBM] WARNING: facts_client not initialized, skipping governance log")
        return factsheet_id

    def _write():
        # Get the GraphSAGE model asset from the governance registry
        # external_model=True because GraphSAGE runs outside Watson ML
        model = facts_client.assets.get_model(
            model_id="graphsage-fraud-v1",
            container_type="space" if WATSONX_SPACE_ID else "project",
            container_id=WATSONX_SPACE_ID or WATSONX_PROJECT_ID,
        )

        # Write all inference facts as custom key-value pairs.
        # These show up in the IBM watsonx.governance dashboard
        # under the model's factsheet tab.
        model.set_custom_facts({
            "factsheet_id":    factsheet_id,
            "claim_token":     claim_token,
            "model_version":   "graphsage-v1.0",
            "combined_score":  float(analysis.combined_score),
            "gnn_score":       float(analysis.gnn_score),
            "isolation_score": float(analysis.isolation_score),
            "risk_level":      analysis.risk_level,
            "adjuster_id":     adjuster_id,
            "decision":        decision,
            "timestamp":       datetime.utcnow().isoformat(),
        })

        return factsheet_id

    return await asyncio.to_thread(_write)


def _mock_log_factsheet(claim_token: str, analysis: FraudAnalysisResult, adjuster_id: str) -> str:
    factsheet_id = str(uuid.uuid4())[:8].upper()
    entry = {
        "factsheet_id":   factsheet_id,
        "claim_token":    claim_token,
        "timestamp":      datetime.utcnow().isoformat(),
        "model_version":  "graphsage-v1.0-mock",
        "combined_score": analysis.combined_score,
        "risk_level":     analysis.risk_level,
        "adjuster_id":    adjuster_id,
        "decision":       "FLAGGED" if analysis.combined_score >= 60 else "APPROVED",
    }
    existing = []
    if LOCAL_FACTSHEETS_PATH.exists():
        with open(LOCAL_FACTSHEETS_PATH) as f:
            existing = json.load(f)
    existing.insert(0, entry)
    existing = existing[:50]
    with open(LOCAL_FACTSHEETS_PATH, "w") as f:
        json.dump(existing, f, indent=2)
    return factsheet_id



# FUNCTION 3 — Fetch factsheets from watsonx.governance
# Called by: api/routes/claims.py  GET /factsheets
# Output: list of FactsheetEntry
async def get_factsheets(limit: int = 10) -> list[FactsheetEntry]:
    if USE_MOCK:
        return _mock_get_factsheets(limit)
    return await _real_get_factsheets(limit)


async def _real_get_factsheets(limit: int) -> list[FactsheetEntry]:
    safe_limit = max(1, min(int(limit), 50))

    if facts_client is None:
        print("[IBM] WARNING: facts_client not initialized, returning empty factsheets")
        return []

    def _read():
        model = facts_client.assets.get_model(
            model_id="graphsage-fraud-v1",
            container_type="space" if WATSONX_SPACE_ID else "project",
            container_id=WATSONX_SPACE_ID or WATSONX_PROJECT_ID,
        )

        # get_custom_facts() returns a dict or list of dicts
        # depending on how many runs have been logged
        raw  = model.get_custom_facts()
        runs = raw if isinstance(raw, list) else [raw]

        entries = []
        for run in runs[:safe_limit]:
            try:
                entries.append(FactsheetEntry(
                    factsheet_id  = run.get("factsheet_id", str(uuid.uuid4())[:8].upper()),
                    claim_token   = run.get("claim_token", "UNKNOWN"),
                    timestamp     = run.get("timestamp", datetime.utcnow().isoformat()),
                    model_version = run.get("model_version", "graphsage-v1.0"),
                    combined_score= float(run.get("combined_score", 0)),
                    risk_level    = run.get("risk_level", "UNKNOWN"),
                    adjuster_id   = run.get("adjuster_id", "UNKNOWN"),
                    decision      = run.get("decision", "UNKNOWN"),
                ))
            except Exception as e:
                print(f"[IBM] WARNING: Could not parse factsheet entry: {e}")
                continue

        return entries

    return await asyncio.to_thread(_read)


def _mock_get_factsheets(limit: int) -> list[FactsheetEntry]:
    if not LOCAL_FACTSHEETS_PATH.exists():
        return _seed_mock_factsheets()
    with open(LOCAL_FACTSHEETS_PATH) as f:
        data = json.load(f)
    return [FactsheetEntry(**entry) for entry in data[:limit]]


def _seed_mock_factsheets() -> list[FactsheetEntry]:
    """Hardcoded fallback so FactsheetPanel is never empty in mock mode."""
    entries = [
        {"factsheet_id": "A1B2C3D4", "claim_token": "CLAIM_001", "timestamp": "2024-06-15T09:23:11",
         "model_version": "graphsage-v1.0-mock", "combined_score": 91.0,
         "risk_level": "CRITICAL", "adjuster_id": "adj_001", "decision": "FLAGGED"},
        {"factsheet_id": "E5F6G7H8", "claim_token": "CLAIM_002", "timestamp": "2024-06-15T10:11:44",
         "model_version": "graphsage-v1.0-mock", "combined_score": 12.0,
         "risk_level": "LOW",      "adjuster_id": "adj_002", "decision": "APPROVED"},
        {"factsheet_id": "I9J0K1L2", "claim_token": "CLAIM_003", "timestamp": "2024-06-15T11:05:02",
         "model_version": "graphsage-v1.0-mock", "combined_score": 68.0,
         "risk_level": "HIGH",     "adjuster_id": "adj_001", "decision": "FLAGGED"},
    ]
    return [FactsheetEntry(**e) for e in entries]