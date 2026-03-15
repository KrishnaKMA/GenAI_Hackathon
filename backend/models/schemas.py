"""
Pydantic schemas -- all API request/response models.
These are the CONTRACTS between frontend, backend, and teammate interfaces.
Do NOT rename fields without updating ml_interface.py and ibm_interface.py.
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────
# GRAPH PRIMITIVES
# ─────────────────────────────────────────────────────────

class GraphNode(BaseModel):
    id: str = Field(..., description="Anonymized token ID, e.g. CLAIMANT_A3F9")
    type: Literal["CLAIMANT", "PROVIDER", "REPAIR_SHOP", "ADJUSTER"]
    fraud_score: float = Field(..., ge=0, le=100)
    claim_count: int = Field(..., ge=0)
    is_flagged: bool

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "CLAIMANT_A3F9",
                "type": "CLAIMANT",
                "fraud_score": 91.0,
                "claim_count": 3,
                "is_flagged": True,
            }
        }
    }


class GraphEdge(BaseModel):
    source: str
    target: str
    weight: int = Field(..., ge=0, description="Number of shared interactions")
    edge_type: Literal["repaired_by", "treated_by", "referred_to", "shared_incident", "filed_by"]
    timestamp: str = Field(..., description="ISO date string")

    model_config = {
        "json_schema_extra": {
            "example": {
                "source": "CLAIMANT_A3F9",
                "target": "SHOP_F2Q7",
                "weight": 3,
                "edge_type": "repaired_by",
                "timestamp": "2024-01-15",
            }
        }
    }


# ─────────────────────────────────────────────────────────
# ML EXPLAINABILITY
# ─────────────────────────────────────────────────────────

class GNNEvidence(BaseModel):
    """One edge the GNNExplainer identified as critical for the fraud score."""
    source_token: str
    target_token: str
    edge_type: str
    importance_score: float = Field(..., ge=0, le=1)
    human_label: str = Field(..., description="Plain-English investigator-readable label")

    model_config = {
        "json_schema_extra": {
            "example": {
                "source_token": "CLAIMANT_A3F9",
                "target_token": "SHOP_F2Q7",
                "edge_type": "repaired_by",
                "importance_score": 0.94,
                "human_label": "Repair shop appears in 12 other suspicious claims",
            }
        }
    }


class SHAPFeature(BaseModel):
    """One SHAP attribution for the Isolation Forest score."""
    feature_name: str
    value: float
    contribution: float = Field(..., ge=0, le=1)
    direction: Literal["increases_risk", "decreases_risk"]

    model_config = {
        "json_schema_extra": {
            "example": {
                "feature_name": "claim_amount_ratio",
                "value": 3.17,
                "contribution": 0.38,
                "direction": "increases_risk",
            }
        }
    }


# ─────────────────────────────────────────────────────────
# FRAUD ANALYSIS RESULT
# Central object passed between ML, IBM, and API layers
# ─────────────────────────────────────────────────────────

class FraudAnalysisResult(BaseModel):
    gnn_score: float = Field(..., ge=0, le=100, description="GraphSAGE fraud probability ×100")
    isolation_score: float = Field(..., ge=0, le=100, description="Isolation Forest anomaly score ×100")
    combined_score: float = Field(..., ge=0, le=100, description="Weighted ensemble score")
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    graph_nodes: List[GraphNode]
    graph_edges: List[GraphEdge]
    gnn_evidence: List[GNNEvidence] = Field(default_factory=list)
    shap_features: List[SHAPFeature] = Field(default_factory=list)

    model_config = {
        "json_schema_extra": {
            "example": {
                "gnn_score": 91.0,
                "isolation_score": 87.0,
                "combined_score": 91.0,
                "risk_level": "CRITICAL",
                "graph_nodes": [],
                "graph_edges": [],
                "gnn_evidence": [],
                "shap_features": [],
            }
        }
    }


# ─────────────────────────────────────────────────────────
# CLAIM INPUT / OUTPUT
# ─────────────────────────────────────────────────────────

class ClaimInput(BaseModel):
    """Raw claim data from the adjuster form or CSV upload."""
    claimant_name: str
    provider_name: str
    repair_shop_name: Optional[str] = None
    claim_amount: float = Field(..., gt=0)
    claim_type: Literal["auto_repair", "medical", "property", "liability"]
    incident_date: str = Field(..., description="ISO date, e.g. 2024-01-15")
    filing_date: str
    prior_claim_count: int = Field(default=0, ge=0)
    days_since_last_claim: Optional[int] = None
    adjuster_id: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "claimant_name": "Jane Smith",
                "provider_name": "City Medical Center",
                "repair_shop_name": "Quick Fix Auto",
                "claim_amount": 47500.0,
                "claim_type": "auto_repair",
                "incident_date": "2024-01-15",
                "filing_date": "2024-01-16",
                "prior_claim_count": 3,
                "days_since_last_claim": 45,
                "adjuster_id": "adj_001",
            }
        }
    }


class ClaimRecord(BaseModel):
    """Stored claim record (PII replaced with tokens)."""
    claim_token: str
    claim_amount: float
    claim_type: str
    incident_date: str
    filing_date: str
    prior_claim_count: int
    days_since_last_claim: Optional[int]
    claimant_token: str
    provider_token: str
    repair_shop_token: Optional[str]
    adjuster_id: str
    status: Literal["pending", "analyzed", "flagged", "approved", "rejected"] = "pending"
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    combined_score: Optional[float] = None
    risk_level: Optional[str] = None


# ─────────────────────────────────────────────────────────
# ENTITY (shared across claimants / providers / shops)
# ─────────────────────────────────────────────────────────

class Entity(BaseModel):
    entity_token: str
    entity_type: Literal["CLAIMANT", "PROVIDER", "REPAIR_SHOP"]
    claim_count: int = 0
    fraud_score: float = 0.0
    is_flagged: bool = False
    last_seen: Optional[str] = None


# ─────────────────────────────────────────────────────────
# INVESTIGATOR REPORT (full page output)
# ─────────────────────────────────────────────────────────

class InvestigatorReport(BaseModel):
    claim_token: str
    analysis: FraudAnalysisResult
    narrative: str = Field(..., description="Granite LLM or mock narrative text")
    factsheet_id: str
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ─────────────────────────────────────────────────────────
# AGENT STREAMING (WebSocket events)
# ─────────────────────────────────────────────────────────

class AgentStepUpdate(BaseModel):
    step_id: int = Field(..., ge=1, le=4)
    name: str
    status: Literal["pending", "running", "complete", "error"]
    result: Optional[str] = None
    is_warning: Optional[bool] = False
    siu_letter: Optional[str] = None


class AgentJob(BaseModel):
    job_id: str
    claim_token: str
    triggered_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    status: Literal["running", "complete", "error"] = "running"
    steps: List[AgentStepUpdate] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────
# IBM GOVERNANCE FACTSHEET ENTRY
# ─────────────────────────────────────────────────────────

class FactsheetEntry(BaseModel):
    factsheet_id: str
    claim_token: str
    timestamp: str
    model_version: str
    combined_score: float
    risk_level: str
    adjuster_id: str
    decision: Literal["FLAGGED", "APPROVED"]

    model_config = {
        "protected_namespaces": (),
        "json_schema_extra": {
            "example": {
                "factsheet_id": "A1B2C3D4",
                "claim_token": "CLAIM_001",
                "timestamp": "2024-06-15T09:23:11",
                "model_version": "graphsage-v1.0-mock",
                "combined_score": 91.0,
                "risk_level": "CRITICAL",
                "adjuster_id": "adj_001",
                "decision": "FLAGGED",
            }
        }
    }


# ─────────────────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────────────────

class User(BaseModel):
    user_id: str
    username: str
    role: Literal["adjuster", "investigator", "admin"]
    totp_enabled: bool = False
    totp_secret: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class TokenPayload(BaseModel):
    sub: str          # username
    role: str
    exp: int          # unix timestamp


class LoginRequest(BaseModel):
    username: str
    password: str
    totp_code: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


class HealthResponse(BaseModel):
    status: str
    mock_ml: bool
    mock_ibm: bool
    version: str = "1.0.0"
