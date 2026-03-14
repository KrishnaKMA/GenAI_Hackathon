"""
Claim ingestion pipeline.
Receives raw ClaimInput (with real PII), tokenizes everything,
stores the anonymized record to the database, and returns
the claim_data dict ready for ml_interface.run_fraud_analysis().
"""

from datetime import datetime
from models.schemas import ClaimInput, ClaimRecord
from core.security import PiiTokenizer
from core import database as db


async def ingest_claim(claim: ClaimInput) -> ClaimRecord:
    """
    Full pipeline:
    1. Tokenize all PII fields
    2. Build ClaimRecord (no PII)
    3. Upsert entities in DB
    4. Insert claim record in DB
    5. Return ClaimRecord
    """
    tokenizer = PiiTokenizer()

    # Tokenize PII
    claim_token       = tokenizer.tokenize("CLAIM",    claim.claimant_name + claim.incident_date)
    claimant_token    = tokenizer.tokenize("CLAIMANT", claim.claimant_name)
    provider_token    = tokenizer.tokenize("PROVIDER", claim.provider_name)
    repair_shop_token = (
        tokenizer.tokenize("SHOP", claim.repair_shop_name)
        if claim.repair_shop_name else None
    )

    record = ClaimRecord(
        claim_token           = claim_token,
        claim_amount          = claim.claim_amount,
        claim_type            = claim.claim_type,
        incident_date         = claim.incident_date,
        filing_date           = claim.filing_date,
        prior_claim_count     = claim.prior_claim_count,
        days_since_last_claim = claim.days_since_last_claim,
        claimant_token        = claimant_token,
        provider_token        = provider_token,
        repair_shop_token     = repair_shop_token,
        adjuster_id           = claim.adjuster_id,
        status                = "pending",
        created_at            = datetime.utcnow().isoformat(),
    )

    # Insert into DB (ignore if claim_token already exists)
    await db.execute(
        """INSERT OR IGNORE INTO claims
           (claim_token, claim_amount, claim_type, incident_date, filing_date,
            prior_claim_count, days_since_last_claim, claimant_token,
            provider_token, repair_shop_token, adjuster_id, status, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            record.claim_token, record.claim_amount, record.claim_type,
            record.incident_date, record.filing_date, record.prior_claim_count,
            record.days_since_last_claim, record.claimant_token,
            record.provider_token, record.repair_shop_token,
            record.adjuster_id, record.status, record.created_at,
        ),
    )

    # Upsert entities
    await _upsert_entity(claimant_token, "CLAIMANT")
    await _upsert_entity(provider_token, "PROVIDER")
    if repair_shop_token:
        await _upsert_entity(repair_shop_token, "REPAIR_SHOP")

    return record


async def _upsert_entity(token: str, entity_type: str) -> None:
    """Insert entity if new, increment claim_count if existing."""
    existing = await db.fetch_one(
        "SELECT claim_count FROM entities WHERE entity_token = ?", (token,)
    )
    now = datetime.utcnow().isoformat()
    if existing:
        await db.execute(
            "UPDATE entities SET claim_count = claim_count + 1, last_seen = ? WHERE entity_token = ?",
            (now, token),
        )
    else:
        await db.execute(
            "INSERT INTO entities (entity_token, entity_type, claim_count, fraud_score, is_flagged, last_seen) "
            "VALUES (?,?,1,0.0,0,?)",
            (token, entity_type, now),
        )


def build_claim_data_dict(record: ClaimRecord) -> dict:
    """
    Converts a ClaimRecord into the flat dict that ml_interface expects.
    This is the exact shape Teammate A will receive in _real_analysis().
    """
    return {
        "claim_token":          record.claim_token,
        "claim_amount":         record.claim_amount,
        "claim_type":           record.claim_type,
        "incident_date":        record.incident_date,
        "filing_date":          record.filing_date,
        "claimant_token":       record.claimant_token,
        "provider_token":       record.provider_token,
        "repair_shop_token":    record.repair_shop_token or "",
        "prior_claim_count":    record.prior_claim_count,
        "days_since_last_claim": record.days_since_last_claim or 0,
        "adjuster_id":          record.adjuster_id,
    }


async def update_claim_score(claim_token: str, combined_score: float, risk_level: str) -> None:
    """Update a claim's risk score and status after ML analysis."""
    status = "flagged" if combined_score >= 60 else "approved"
    await db.execute(
        "UPDATE claims SET combined_score=?, risk_level=?, status=? WHERE claim_token=?",
        (combined_score, risk_level, status, claim_token),
    )
