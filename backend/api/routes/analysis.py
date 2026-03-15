"""
Analysis routes.
POST /analyze/{claim_token}  -> run fraud analysis, return InvestigatorReport
GET  /analyze/{claim_token}  -> get cached report from inference_log
POST /analyze/batch          -> analyze multiple claims (background task)
"""

from fastapi import APIRouter, Depends, BackgroundTasks
from models.schemas import InvestigatorReport, FraudAnalysisResult, TokenPayload
from services.ml_interface import run_fraud_analysis
from services.report_generator import generate_report
from services.claim_ingestor import build_claim_data_dict, update_claim_score
from services.graph_builder import update_entity_scores
from core import database as db
from core.exceptions import ClaimNotFound, AnalysisError
from api.deps import require_adjuster

router = APIRouter(tags=["Analysis"])


@router.post("/analyze/{claim_token}", response_model=InvestigatorReport)
async def analyze_claim(
    claim_token: str,
    user: TokenPayload = Depends(require_adjuster),
):
    """
    Run full fraud analysis on a claim.
    1. Fetch claim record from DB
    2. Run ML model (mock or real)
    3. Generate Granite narrative (mock or real)
    4. Log to IBM governance factsheet
    5. Return InvestigatorReport

    If score >= 75, the frontend will auto-trigger the fraud agent
    via WebSocket /ws/agent/{claim_token}.
    """
    # Fetch claim record
    row = await db.fetch_one(
        "SELECT * FROM claims WHERE claim_token = ?", (claim_token,)
    )
    if not row:
        raise ClaimNotFound(claim_token)

    claim_data = dict(row)

    try:
        # Run ML analysis
        analysis: FraudAnalysisResult = await run_fraud_analysis(claim_data)
    except Exception as e:
        raise AnalysisError(f"ML analysis failed: {str(e)}")

    # Update claim status in DB
    await update_claim_score(claim_token, analysis.combined_score, analysis.risk_level)
    await update_entity_scores(analysis.graph_nodes)

    # Generate full report (narrative + factsheet)
    report = await generate_report(claim_token, analysis, user.sub)

    return report


@router.get("/analyze/{claim_token}/cached", response_model=dict)
async def get_cached_analysis(
    claim_token: str,
    user: TokenPayload = Depends(require_adjuster),
):
    """Fetch the most recent cached inference log for a claim."""
    row = await db.fetch_one(
        """SELECT * FROM inference_log
           WHERE claim_token = ?
           ORDER BY created_at DESC LIMIT 1""",
        (claim_token,),
    )
    if not row:
        raise ClaimNotFound(f"No analysis found for {claim_token}")
    return row


@router.post("/analyze/demo/{risk_level}", response_model=InvestigatorReport)
async def analyze_demo(
    risk_level: str,
    user: TokenPayload = Depends(require_adjuster),
):
    """
    Demo endpoint -- generates a fake analysis for the given risk level.
    risk_level: LOW | MEDIUM | HIGH | CRITICAL
    Used by the demo button on the dashboard. No DB lookup needed.
    """
    demo_claims = {
        "LOW":      {"claim_token": "DEMO_LOW_001",  "claim_amount": 5000,  "prior_claim_count": 0, "claim_type": "auto_repair", "incident_date": "2024-05-01", "filing_date": "2024-05-03", "claimant_token": "CLAIMANT_DEMO1", "provider_token": "PROVIDER_DEMO1", "repair_shop_token": "", "adjuster_id": user.sub, "days_since_last_claim": 0},
        "MEDIUM":   {"claim_token": "DEMO_MED_001",  "claim_amount": 18000, "prior_claim_count": 1, "claim_type": "medical",    "incident_date": "2024-04-10", "filing_date": "2024-04-11", "claimant_token": "CLAIMANT_DEMO2", "provider_token": "PROVIDER_DEMO2", "repair_shop_token": "", "adjuster_id": user.sub, "days_since_last_claim": 120},
        "HIGH":     {"claim_token": "DEMO_HIGH_001", "claim_amount": 32000, "prior_claim_count": 2, "claim_type": "auto_repair","incident_date": "2024-03-15", "filing_date": "2024-03-16", "claimant_token": "CLAIMANT_DEMO3", "provider_token": "PROVIDER_DEMO3", "repair_shop_token": "SHOP_DEMO1",    "adjuster_id": user.sub, "days_since_last_claim": 45},
        "CRITICAL": {"claim_token": "DEMO_CRIT_001", "claim_amount": 52000, "prior_claim_count": 4, "claim_type": "auto_repair","incident_date": "2024-01-15", "filing_date": "2024-01-16", "claimant_token": "CLAIMANT_DEMO4", "provider_token": "PROVIDER_DEMO4", "repair_shop_token": "SHOP_DEMO2",    "adjuster_id": user.sub, "days_since_last_claim": 28},
    }

    level = risk_level.upper()
    if level not in demo_claims:
        level = "HIGH"

    claim_data = demo_claims[level]
    analysis = await run_fraud_analysis(claim_data)
    report = await generate_report(claim_data["claim_token"], analysis, user.sub)
    return report
