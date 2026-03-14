"""
+==========================================================+
|           ML MODEL INTERFACE -- TEAMMATE A                |
|                                                          |
|  Hi! This is the ONLY file you need to edit.             |
|                                                          |
|  STEP 1: Put your trained files here:                    |
|    • backend/models/gnn/pretrained/weights.pt            |
|    • backend/models/anomaly/iforest.pkl                  |
|                                                          |
|  STEP 2: Fill in the two functions marked                |
|    # TEAMMATE A: YOUR CODE GOES HERE                     |
|                                                          |
|  STEP 3: Test it:                                        |
|    curl -X POST http://localhost:8000/analyze/TEST_TOKEN |
|    Check logs -- should say: [ML] Using REAL model        |
|                                                          |
|  DO NOT touch any other file. Krishna handles the rest.  |
+==========================================================+
"""

import os
from pathlib import Path
from models.schemas import FraudAnalysisResult, GNNEvidence, SHAPFeature, GraphNode, GraphEdge

# ─────────────────────────────────────────────────────────
# AUTO-DETECTION: switches between mock and real automatically
# When weights.pt exists -> real model runs
# When weights.pt missing -> mock runs (safe for development)
# ─────────────────────────────────────────────────────────
GNN_WEIGHTS_PATH = Path("models/gnn/pretrained/weights.pt")
IFOREST_PATH     = Path("models/anomaly/iforest.pkl")
USE_MOCK         = not (GNN_WEIGHTS_PATH.exists() and IFOREST_PATH.exists())

if USE_MOCK:
    print("[ML] WARNING:  Model files not found -- using MOCK data")
    print(f"[ML] Missing: {GNN_WEIGHTS_PATH}")
    print(f"[ML] Missing: {IFOREST_PATH}")
else:
    print("[ML] OK: Model files found -- using REAL model")


# ─────────────────────────────────────────────────────────
# # TEAMMATE A: LOAD YOUR MODELS HERE (only runs if files exist)
# Replace the pass statements with your actual loading code
# ─────────────────────────────────────────────────────────
gnn_model     = None  # # TEAMMATE A: load your GraphSAGE here
iforest_model = None  # # TEAMMATE A: load your IForest here

if not USE_MOCK:
    pass
    # # TEAMMATE A: YOUR MODEL LOADING CODE GOES HERE
    # Example:
    # import torch
    # import pickle
    # from models.gnn.graphsage import GraphSAGE
    # gnn_model = GraphSAGE(in_channels=12, hidden_channels=64, out_channels=1)
    # gnn_model.load_state_dict(torch.load(GNN_WEIGHTS_PATH))
    # gnn_model.eval()
    # with open(IFOREST_PATH, "rb") as f:
    #     iforest_model = pickle.load(f)


# ─────────────────────────────────────────────────────────
# MAIN FUNCTION -- called by the API route
# Input:  claim_data dict (already tokenized, no real PII)
# Output: FraudAnalysisResult (shape defined in schemas.py)
# ─────────────────────────────────────────────────────────
async def run_fraud_analysis(claim_data: dict) -> FraudAnalysisResult:
    if USE_MOCK:
        return _mock_analysis(claim_data)
    else:
        return await _real_analysis(claim_data)


# ─────────────────────────────────────────────────────────
# # TEAMMATE A: YOUR REAL ANALYSIS GOES IN THIS FUNCTION
# This runs ONLY when weights.pt and iforest.pkl exist
# claim_data keys: claim_token, claim_amount, claim_type,
#   incident_date, filing_date, claimant_token, provider_token,
#   repair_shop_token, prior_claim_count, days_since_last_claim
# ─────────────────────────────────────────────────────────
async def _real_analysis(claim_data: dict) -> FraudAnalysisResult:
    # # TEAMMATE A: REPLACE THIS ENTIRE FUNCTION BODY
    # Steps you need to implement:
    # 1. Build graph from claim_data using graph_builder helpers
    # 2. Run gnn_model inference -> get gnn_score + graph embeddings
    # 3. Run iforest_model.predict() on tabular features -> isolation_score
    # 4. Run GNNExplainer -> get top 5 important edges
    # 5. Run SHAP on iforest -> get top 5 feature attributions
    # 6. Return FraudAnalysisResult with all fields populated
    #
    # The FraudAnalysisResult schema is in backend/models/schemas.py
    # Graph helpers are in backend/services/graph_builder.py
    # Ask Krishna if you need anything from the database.
    raise NotImplementedError("Teammate A: implement _real_analysis()")


# ─────────────────────────────────────────────────────────
# MOCK FUNCTION -- Krishna built this so the app works now
# Returns realistic fake scores based on claim fields
# Teammate A: don't touch this, just implement _real_analysis
# ─────────────────────────────────────────────────────────
def _mock_analysis(claim_data: dict) -> FraudAnalysisResult:
    amount = float(claim_data.get("claim_amount", 0))
    prior  = int(claim_data.get("prior_claim_count", 0))

    # Score logic: higher amount + more prior claims = higher risk
    if prior >= 3 or amount > 45000:
        gnn_score   = 91.0
        iso_score   = 87.0
        combined    = 91.0
        risk        = "CRITICAL"
        nodes       = _mock_ring_nodes()
        edges       = _mock_ring_edges()
    elif prior >= 2 or amount > 25000:
        gnn_score   = 68.0
        iso_score   = 71.0
        combined    = 69.0
        risk        = "HIGH"
        nodes       = _mock_solo_nodes()
        edges       = _mock_solo_edges()
    elif amount > 10000:
        gnn_score   = 44.0
        iso_score   = 38.0
        combined    = 41.0
        risk        = "MEDIUM"
        nodes       = _mock_solo_nodes()
        edges       = _mock_solo_edges()
    else:
        gnn_score   = 12.0
        iso_score   = 8.0
        combined    = 10.0
        risk        = "LOW"
        nodes       = _mock_clean_nodes()
        edges       = _mock_clean_edges()

    return FraudAnalysisResult(
        gnn_score        = gnn_score,
        isolation_score  = iso_score,
        combined_score   = combined,
        risk_level       = risk,
        graph_nodes      = nodes,
        graph_edges      = edges,
        gnn_evidence     = _mock_evidence(risk),
        shap_features    = _mock_shap(amount, prior),
    )


def _mock_ring_nodes():
    return [
        GraphNode(id="CLAIMANT_A3F9", type="CLAIMANT",    fraud_score=91, claim_count=3, is_flagged=True),
        GraphNode(id="CLAIMANT_B7K2", type="CLAIMANT",    fraud_score=88, claim_count=2, is_flagged=True),
        GraphNode(id="CLAIMANT_C1M8", type="CLAIMANT",    fraud_score=85, claim_count=4, is_flagged=True),
        GraphNode(id="PROVIDER_D4N1", type="PROVIDER",    fraud_score=72, claim_count=9, is_flagged=True),
        GraphNode(id="PROVIDER_E9P3", type="PROVIDER",    fraud_score=45, claim_count=4, is_flagged=False),
        GraphNode(id="SHOP_F2Q7",     type="REPAIR_SHOP", fraud_score=95, claim_count=12,is_flagged=True),
    ]

def _mock_ring_edges():
    return [
        GraphEdge(source="CLAIMANT_A3F9", target="SHOP_F2Q7",    weight=3, edge_type="repaired_by",  timestamp="2024-01-15"),
        GraphEdge(source="CLAIMANT_B7K2", target="SHOP_F2Q7",    weight=2, edge_type="repaired_by",  timestamp="2024-02-03"),
        GraphEdge(source="CLAIMANT_C1M8", target="SHOP_F2Q7",    weight=4, edge_type="repaired_by",  timestamp="2024-03-21"),
        GraphEdge(source="CLAIMANT_A3F9", target="PROVIDER_D4N1",weight=2, edge_type="treated_by",   timestamp="2024-01-16"),
        GraphEdge(source="CLAIMANT_B7K2", target="PROVIDER_D4N1",weight=1, edge_type="treated_by",   timestamp="2024-02-04"),
        GraphEdge(source="CLAIMANT_C1M8", target="PROVIDER_E9P3",weight=2, edge_type="treated_by",   timestamp="2024-03-22"),
        GraphEdge(source="PROVIDER_D4N1", target="SHOP_F2Q7",    weight=5, edge_type="referred_to",  timestamp="2024-01-10"),
        GraphEdge(source="CLAIMANT_A3F9", target="CLAIMANT_B7K2",weight=1, edge_type="shared_incident",timestamp="2024-01-20"),
    ]

def _mock_clean_nodes():
    return [
        GraphNode(id="CLAIMANT_X1A2", type="CLAIMANT", fraud_score=12, claim_count=1, is_flagged=False),
        GraphNode(id="PROVIDER_Y3B4", type="PROVIDER", fraud_score=8,  claim_count=2, is_flagged=False),
    ]

def _mock_clean_edges():
    return [GraphEdge(source="CLAIMANT_X1A2", target="PROVIDER_Y3B4", weight=1, edge_type="treated_by", timestamp="2024-06-10")]

def _mock_solo_nodes():
    return [
        GraphNode(id="CLAIMANT_S5C6", type="CLAIMANT", fraud_score=68, claim_count=4, is_flagged=True),
        GraphNode(id="PROVIDER_T7D8", type="PROVIDER", fraud_score=22, claim_count=5, is_flagged=False),
        GraphNode(id="PROVIDER_U9E0", type="PROVIDER", fraud_score=18, claim_count=3, is_flagged=False),
        GraphNode(id="PROVIDER_V1F2", type="PROVIDER", fraud_score=15, claim_count=2, is_flagged=False),
    ]

def _mock_solo_edges():
    return [
        GraphEdge(source="CLAIMANT_S5C6", target="PROVIDER_T7D8", weight=2, edge_type="treated_by", timestamp="2024-03-01"),
        GraphEdge(source="CLAIMANT_S5C6", target="PROVIDER_U9E0", weight=1, edge_type="treated_by", timestamp="2024-04-15"),
        GraphEdge(source="CLAIMANT_S5C6", target="PROVIDER_V1F2", weight=1, edge_type="treated_by", timestamp="2024-05-22"),
    ]

def _mock_evidence(risk: str):
    if risk == "CRITICAL":
        return [
            GNNEvidence(source_token="CLAIMANT_A3F9", target_token="SHOP_F2Q7",    edge_type="repaired_by",  importance_score=0.94, human_label="Repair shop appears in 12 other suspicious claims"),
            GNNEvidence(source_token="CLAIMANT_B7K2", target_token="SHOP_F2Q7",    edge_type="repaired_by",  importance_score=0.91, human_label="3 unrelated claimants share same repair shop"),
            GNNEvidence(source_token="PROVIDER_D4N1", target_token="SHOP_F2Q7",    edge_type="referred_to",  importance_score=0.87, human_label="Provider exclusively refers to flagged shop"),
            GNNEvidence(source_token="CLAIMANT_A3F9", target_token="CLAIMANT_B7K2",edge_type="shared_incident",importance_score=0.76, human_label="Claimants share incident but no police report"),
            GNNEvidence(source_token="CLAIMANT_C1M8", target_token="SHOP_F2Q7",    edge_type="repaired_by",  importance_score=0.71, human_label="4th claim at same shop in 3 months"),
        ]
    return [
        GNNEvidence(source_token="CLAIMANT_S5C6", target_token="PROVIDER_T7D8", edge_type="treated_by", importance_score=0.65, human_label="Claimant filed 4 claims in 6 months"),
        GNNEvidence(source_token="CLAIMANT_S5C6", target_token="PROVIDER_U9E0", edge_type="treated_by", importance_score=0.58, human_label="Multiple providers for same incident"),
    ]

def _mock_shap(amount: float, prior: int):
    return [
        SHAPFeature(feature_name="claim_amount_ratio",     value=round(amount/15000, 2), contribution=0.38, direction="increases_risk"),
        SHAPFeature(feature_name="prior_claim_count",      value=float(prior),           contribution=0.29, direction="increases_risk"),
        SHAPFeature(feature_name="days_incident_to_filing",value=1.0,                    contribution=0.18, direction="increases_risk"),
        SHAPFeature(feature_name="provider_fraud_rate",    value=0.34,                   contribution=0.11, direction="increases_risk"),
        SHAPFeature(feature_name="policy_age_years",       value=2.1,                    contribution=0.08, direction="decreases_risk"),
    ]
