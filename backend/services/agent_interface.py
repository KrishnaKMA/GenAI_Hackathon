"""
+==========================================================+
|              FRAUD AGENT -- KRISHNA + TEAMMATES           |
|                                                          |
|  The agent runs automatically when score >= 75.          |
|  It completes 4 steps and streams them to the frontend.  |
|                                                          |
|  MOCK: runs with simulated delays, always works          |
|  REAL: needs Teammate B's IBM setup for Db2 task storage |
|                                                          |
|  To make Step 2 real: Teammate B connects business API   |
|  To make Step 4 real: Teammate B connects Db2 tasks table|
+==========================================================+
"""

import uuid
import asyncio
from datetime import datetime, timedelta
from typing import AsyncGenerator
from models.schemas import FraudAnalysisResult, AgentStepUpdate


async def run_fraud_agent(
    claim_token: str,
    analysis: FraudAnalysisResult
) -> AsyncGenerator[AgentStepUpdate, None]:
    """
    Streams 4 agent steps to the WebSocket client.
    Each step yields a 'running' update then a 'complete' update.
    The frontend renders each step card as it arrives.
    """
    job_id = str(uuid.uuid4())[:8].upper()

    # ─────────────────────────────────────────────────────
    # STEP 1 -- Alert (instant)
    # ─────────────────────────────────────────────────────
    yield AgentStepUpdate(step_id=1, name="Alert Sent", status="running")
    await asyncio.sleep(0.8)
    yield AgentStepUpdate(
        step_id=1,
        name="Alert Sent",
        status="complete",
        result=f"Priority alert logged · Case {claim_token[:8].upper()} · Job {job_id}",
    )

    # ─────────────────────────────────────────────────────
    # STEP 2 -- Business registry verification
    # # TEAMMATE B: replace mock with real Canadian Business Registry API call
    # URL: https://api.open.canada.ca/action/datastore_search
    # resource_id: "1b5c4026-5a2c-4e3f-9867-0ee77f5c0b1a"  (business registry)
    # Params: {"q": repair_shop_name, "limit": 1}
    # If result["total"] == 0 -> UNREGISTERED
    # ─────────────────────────────────────────────────────
    yield AgentStepUpdate(step_id=2, name="Business Verified", status="running")
    await asyncio.sleep(1.5)

    # Extract repair shop from flagged nodes for verification
    flagged_shops = [n for n in analysis.graph_nodes if n.type == "REPAIR_SHOP" and n.is_flagged]
    if flagged_shops:
        shop_id = flagged_shops[0].id
        yield AgentStepUpdate(
            step_id=2,
            name="Business Verified",
            status="complete",
            result=f"WARNING: UNREGISTERED -- {shop_id} not found in Canadian Business Registry",
            is_warning=True,
        )
    else:
        yield AgentStepUpdate(
            step_id=2,
            name="Business Verified",
            status="complete",
            result="OK: All entities verified in Canadian Business Registry",
        )

    # ─────────────────────────────────────────────────────
    # STEP 3 -- SIU referral letter (2s -- Granite call or mock)
    # Currently mock; when Teammate B sets up watsonx,
    # this could use Granite to personalize the letter
    # ─────────────────────────────────────────────────────
    yield AgentStepUpdate(step_id=3, name="SIU Letter Drafted", status="running")
    await asyncio.sleep(2.0)
    letter = _generate_siu_letter(claim_token, analysis)
    yield AgentStepUpdate(
        step_id=3,
        name="SIU Letter Drafted",
        status="complete",
        result="SIU referral letter ready · Click to view",
        siu_letter=letter,
    )

    # ─────────────────────────────────────────────────────
    # STEP 4 -- Schedule SIU task (instant)
    # # TEAMMATE B: replace with real Db2 insert into tasks table:
    # INSERT INTO tasks (claim_token, assigned_to, due_at, status, created_at)
    # VALUES (?, 'SIU_TEAM', ?, 'open', ?)
    # ─────────────────────────────────────────────────────
    yield AgentStepUpdate(step_id=4, name="Task Scheduled", status="running")
    await asyncio.sleep(0.5)
    due = (datetime.utcnow() + timedelta(hours=48)).strftime("%Y-%m-%d %H:%M UTC")
    yield AgentStepUpdate(
        step_id=4,
        name="Task Scheduled",
        status="complete",
        result=f"SIU team assigned · Due: {due}",
    )


def _generate_siu_letter(claim_token: str, analysis: FraudAnalysisResult) -> str:
    """
    Generates the SIU referral letter text.
    In production, this could be replaced with a Granite LLM call
    via ibm_interface.generate_narrative() for a more customized letter.
    """
    flagged_nodes = [n for n in analysis.graph_nodes if n.is_flagged]
    evidence_lines = "\n".join(f"• {e.human_label}" for e in analysis.gnn_evidence[:3])
    entity_lines = "\n".join(
        f"• {n.id} ({n.type}) -- Fraud Score: {n.fraud_score}/100"
        for n in flagged_nodes
    )
    priority = "CRITICAL" if analysis.combined_score >= 85 else "HIGH"

    return f"""SPECIAL INVESTIGATIONS UNIT REFERRAL
Case Reference: {claim_token[:8].upper()}
Date: {datetime.utcnow().strftime('%B %d, %Y')}
Priority: {priority}

Dear SIU Team,

This referral is submitted regarding insurance claim {claim_token[:8].upper()} \
which has been flagged by ClaimShield's AI fraud detection system with a combined \
risk score of {analysis.combined_score}/100 ({analysis.risk_level}).

SUMMARY OF FINDINGS:
{evidence_lines}

ENTITIES FLAGGED FOR INVESTIGATION:
{entity_lines if entity_lines else "• No individual entities flagged -- review full graph"}

RECOMMENDED ACTIONS:
1. Verify business registration of all flagged repair shops
2. Obtain independent medical assessments for all injury claims
3. Request CCTV footage from incident location and repair facility
4. Cross-reference claimant identities against prior fraud records
5. Issue litigation hold on all associated claim files

This case has been assigned to your queue with a 48-hour investigation deadline.

ClaimShield Automated Fraud Detection System
Powered by IBM watsonx.ai"""
