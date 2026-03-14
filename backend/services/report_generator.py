"""
Report generation orchestrator.
Combines ML analysis + IBM narrative + factsheet logging
into a single InvestigatorReport.
"""

from datetime import datetime
from models.schemas import FraudAnalysisResult, InvestigatorReport
from services import ibm_interface
from core import database as db


async def generate_report(
    claim_token: str,
    analysis: FraudAnalysisResult,
    adjuster_id: str,
) -> InvestigatorReport:
    """
    1. Generate narrative via Granite (or mock)
    2. Log factsheet to IBM governance (or local JSON)
    3. Log inference to local DB
    4. Return complete InvestigatorReport
    """
    # 1. Generate narrative
    narrative = await ibm_interface.generate_narrative(analysis)

    # 2. Log to governance factsheet
    factsheet_id = await ibm_interface.log_factsheet(claim_token, analysis, adjuster_id)

    # 3. Log inference to local DB
    await db.execute(
        """INSERT INTO inference_log
           (claim_token, gnn_score, isolation_score, combined_score,
            risk_level, adjuster_id, factsheet_id, created_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        (
            claim_token,
            analysis.gnn_score,
            analysis.isolation_score,
            analysis.combined_score,
            analysis.risk_level,
            adjuster_id,
            factsheet_id,
            datetime.utcnow().isoformat(),
        ),
    )

    return InvestigatorReport(
        claim_token  = claim_token,
        analysis     = analysis,
        narrative    = narrative,
        factsheet_id = factsheet_id,
        generated_at = datetime.utcnow().isoformat(),
    )
