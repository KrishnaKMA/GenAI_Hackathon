"""
Claims CRUD routes.
POST /claims          -> ingest new claim
GET  /claims          -> list claims (paginated)
GET  /claims/{token}  -> get single claim
GET  /factsheets      -> IBM governance log (FactsheetPanel)
"""

from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from models.schemas import ClaimInput, ClaimRecord, FactsheetEntry, TokenPayload
from services.claim_ingestor import ingest_claim
from services import ibm_interface
from core import database as db
from core.exceptions import ClaimNotFound
from api.deps import require_adjuster, require_investigator

router = APIRouter(tags=["Claims"])


@router.post("/claims", response_model=ClaimRecord)
async def create_claim(
    body: ClaimInput,
    user: TokenPayload = Depends(require_adjuster),
):
    """
    Ingest a new claim. Tokenizes PII, stores record, returns ClaimRecord.
    Run /analyze/{claim_token} afterwards to get fraud scores.
    """
    # Override adjuster_id with authenticated user
    body.adjuster_id = user.sub
    record = await ingest_claim(body)
    return record


@router.get("/claims", response_model=List[dict])
async def list_claims(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: Optional[str] = Query(default=None),
    risk_level: Optional[str] = Query(default=None),
    user: TokenPayload = Depends(require_adjuster),
):
    """
    List all claims with optional filters.
    Returns newest first.
    """
    conditions = []
    params = []

    if status:
        conditions.append("status = ?")
        params.append(status)
    if risk_level:
        conditions.append("risk_level = ?")
        params.append(risk_level)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"SELECT * FROM claims {where} ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = await db.fetch_all(sql, tuple(params))
    return rows


@router.get("/claims/{claim_token}", response_model=dict)
async def get_claim(
    claim_token: str,
    user: TokenPayload = Depends(require_adjuster),
):
    """Get a single claim by token."""
    row = await db.fetch_one(
        "SELECT * FROM claims WHERE claim_token = ?", (claim_token,)
    )
    if not row:
        raise ClaimNotFound(claim_token)
    return row


@router.get("/factsheets", response_model=List[FactsheetEntry])
async def get_factsheets(
    limit: int = Query(default=10, ge=1, le=50),
    user: TokenPayload = Depends(require_adjuster),
):
    """
    Retrieve IBM watsonx.governance factsheet log entries.
    Shows model decisions for AI audit trail (FactsheetPanel).
    When IBM not connected -> returns local JSON mock data.
    """
    return await ibm_interface.get_factsheets(limit)
