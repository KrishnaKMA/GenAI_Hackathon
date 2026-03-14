"""
Agent WebSocket route.
WS /ws/agent/{claim_token}  -> streams AgentStepUpdate events as JSON

Frontend connects here when combined_score >= 75.
The agent runs 4 steps and closes the connection.

Message format (JSON):
{
  "step_id": 1,
  "name": "Alert Sent",
  "status": "complete",
  "result": "...",
  "is_warning": false,
  "siu_letter": null
}
"""

import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.ml_interface import run_fraud_analysis
from services.agent_interface import run_fraud_agent

router = APIRouter(tags=["Agent"])


@router.websocket("/ws/agent/{claim_token}")
async def agent_websocket(websocket: WebSocket, claim_token: str):
    """
    WebSocket endpoint for live agent step streaming.

    The frontend (AgentStatus.tsx) connects here automatically
    when a CRITICAL or HIGH risk analysis completes.

    Protocol:
    1. Client connects
    2. Client sends: {"claim_token": "...", "risk_level": "CRITICAL", ...analysis data...}
    3. Server streams AgentStepUpdate JSON messages for each of 4 steps
    4. Server closes connection when all steps complete
    """
    await websocket.accept()

    try:
        # Receive analysis data from client
        raw = await websocket.receive_text()
        data = json.loads(raw)

        # Reconstruct a minimal FraudAnalysisResult for the agent
        # The frontend sends the full analysis object it received
        from models.schemas import (
            FraudAnalysisResult, GraphNode, GraphEdge, GNNEvidence, SHAPFeature
        )

        analysis = FraudAnalysisResult(
            gnn_score        = data.get("gnn_score", 91.0),
            isolation_score  = data.get("isolation_score", 87.0),
            combined_score   = data.get("combined_score", 91.0),
            risk_level       = data.get("risk_level", "CRITICAL"),
            graph_nodes      = [GraphNode(**n) for n in data.get("graph_nodes", [])],
            graph_edges      = [GraphEdge(**e) for e in data.get("graph_edges", [])],
            gnn_evidence     = [GNNEvidence(**e) for e in data.get("gnn_evidence", [])],
            shap_features    = [SHAPFeature(**f) for f in data.get("shap_features", [])],
        )

        # Stream agent steps
        async for step_update in run_fraud_agent(claim_token, analysis):
            await websocket.send_text(step_update.model_dump_json())

        # Signal completion
        await websocket.send_text(json.dumps({"status": "done"}))

    except WebSocketDisconnect:
        pass  # Client disconnected -- normal, don't log as error
    except Exception as e:
        try:
            await websocket.send_text(json.dumps({
                "status": "error",
                "message": str(e),
            }))
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
