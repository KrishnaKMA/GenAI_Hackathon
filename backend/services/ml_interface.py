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

import math
import os
import pickle
from pathlib import Path
from statistics import mean, pstdev

import numpy as np
import pandas as pd
from models.schemas import FraudAnalysisResult, GNNEvidence, SHAPFeature, GraphNode, GraphEdge
from core import database as db
from services.graph_builder import get_claim_subgraph, build_adjacency_list

try:
    import torch
    import torch.nn.functional as F
    import shap
    from lightgbm import Booster, LGBMClassifier
    from torch_geometric.data import Data
    from torch_geometric.explain import Explainer, GNNExplainer
    from torch_geometric.nn import SAGEConv
    ML_IMPORTS_AVAILABLE = True
except ImportError:
    torch = None
    F = None
    shap = None
    Booster = LGBMClassifier = None
    Data = None
    Explainer = GNNExplainer = None
    SAGEConv = None
    ML_IMPORTS_AVAILABLE = False

# ─────────────────────────────────────────────────────────
# AUTO-DETECTION: switches between mock and real automatically
# When weights.pt exists -> real model runs
# When weights.pt missing -> mock runs (safe for development)
# ─────────────────────────────────────────────────────────
GNN_WEIGHTS_PATH = Path("models/gnn/pretrained/weights.pt")
IFOREST_PATH     = Path("models/anomaly/iforest.pkl")
MODEL_FILES_PRESENT = GNN_WEIGHTS_PATH.exists() and IFOREST_PATH.exists()
USE_MOCK = not (MODEL_FILES_PRESENT and ML_IMPORTS_AVAILABLE)
ENABLE_GNN_EXPLAINER = os.getenv("ML_ENABLE_GNN_EXPLAINER", "false").strip().lower() == "true"

if USE_MOCK:
    if not MODEL_FILES_PRESENT:
        print("[ML] WARNING:  Model files not found -- using MOCK data")
        print(f"[ML] Missing: {GNN_WEIGHTS_PATH}")
        print(f"[ML] Missing: {IFOREST_PATH}")
    elif not ML_IMPORTS_AVAILABLE:
        print("[ML] WARNING: ML dependencies are not installed -- using MOCK data")
else:
    print("[ML] OK: Model files found -- using REAL model")


# ─────────────────────────────────────────────────────────
# # TEAMMATE A: LOAD YOUR MODELS HERE (only runs if files exist)
# Replace the pass statements with your actual loading code
# ─────────────────────────────────────────────────────────
class GraphSAGEFraud(torch.nn.Module if torch else object):
    """
    Runtime copy of Logan's training architecture.
    The checkpoint in weights.pt was trained with this 3-layer GraphSAGE stack.
    """

    def __init__(self, in_ch: int, hidden: int = 256, dropout: float = 0.4):
        super().__init__()
        self.conv1 = SAGEConv(in_ch, hidden)
        self.conv2 = SAGEConv(hidden, hidden * 2)
        self.conv3 = SAGEConv(hidden * 2, hidden)
        self.bn1 = torch.nn.BatchNorm1d(hidden)
        self.bn2 = torch.nn.BatchNorm1d(hidden * 2)
        self.bn3 = torch.nn.BatchNorm1d(hidden)
        self.drop = torch.nn.Dropout(dropout)
        self.head = torch.nn.Linear(hidden, 1)
        self.skip_proj = torch.nn.Linear(in_ch, hidden)

    def forward(self, x, edge_index):
        res = self.skip_proj(x)
        x = self.conv1(x, edge_index)
        x = self.bn1(x).relu()
        x = self.drop(x)
        x = x + res
        x = self.conv2(x, edge_index)
        x = self.bn2(x).relu()
        x = self.drop(x)

        x = self.conv3(x, edge_index)
        x = self.bn3(x).relu()
        x = self.drop(x)
        return self.head(x).squeeze(-1)


class GraphSAGEEmbedder(torch.nn.Module if torch else object):
    def __init__(self, in_ch: int, hidden: int = 256, dropout: float = 0.4):
        super().__init__()
        self.conv1 = SAGEConv(in_ch, hidden)
        self.conv2 = SAGEConv(hidden, hidden * 2)
        self.conv3 = SAGEConv(hidden * 2, hidden)
        self.bn1 = torch.nn.BatchNorm1d(hidden)
        self.bn2 = torch.nn.BatchNorm1d(hidden * 2)
        self.bn3 = torch.nn.BatchNorm1d(hidden)
        self.drop = torch.nn.Dropout(dropout)
        self.skip_proj = torch.nn.Linear(in_ch, hidden)

    def forward(self, x, edge_index):
        res = self.skip_proj(x)
        x = self.conv1(x, edge_index)
        x = self.bn1(x).relu()
        x = self.drop(x)
        x = x + res
        x = self.conv2(x, edge_index)
        x = self.bn2(x).relu()
        x = self.drop(x)
        x = self.conv3(x, edge_index)
        x = self.bn3(x).relu()
        x = self.drop(x)
        return x


BASE_GNN_FEATURES = [
    "log_count",
    "log_avg_amt",
    "std_amount",
    "max_amount",
    "unique_emails",
    "unique_devices",
    "unique_cards",
]
COUNT_FEATURE_NAMES = [f"C{i}_{suffix}" for i in range(1, 15) for suffix in ("mean", "max")]
TIME_FEATURE_NAMES = [f"D{i}_{suffix}" for i in range(1, 16) for suffix in ("mean", "min")]
NETWORK_FEATURE_NAMES = [f"V{i}" for i in range(1, 51)]
BOOLEAN_FEATURE_NAMES = [f"M{i}" for i in range(1, 10)]
GNN_FEATURE_NAMES = (
    BASE_GNN_FEATURES
    + COUNT_FEATURE_NAMES
    + TIME_FEATURE_NAMES
    + NETWORK_FEATURE_NAMES
    + BOOLEAN_FEATURE_NAMES
)
GNN_FEATURE_INDEX = {name: idx for idx, name in enumerate(GNN_FEATURE_NAMES)}


gnn_model = None
lgbm_model = None
lgbm_feature_cols: list[str] = []
lgbm_threshold = 0.5
lgbm_aggregation = "max"
gnn_checkpoint = None
gnn_scaler = None
gnn_embedder = None
shap_explainer = None

if not USE_MOCK:
    try:
        gnn_checkpoint = torch.load(GNN_WEIGHTS_PATH, map_location="cpu", weights_only=False)
        model_state = gnn_checkpoint["model_state"]
        inferred_in_ch = model_state["conv1.lin_l.weight"].shape[1]
        gnn_model = GraphSAGEFraud(in_ch=inferred_in_ch)
        gnn_model.load_state_dict(model_state)
        gnn_model.eval()
        gnn_scaler = gnn_checkpoint.get("scaler")

        gnn_embedder = GraphSAGEEmbedder(in_ch=inferred_in_ch)
        gnn_embedder.load_state_dict(
            {k: v for k, v in model_state.items() if k in gnn_embedder.state_dict()},
            strict=False,
        )
        gnn_embedder.eval()

        with open(IFOREST_PATH, "rb") as f:
            lgbm_bundle = pickle.load(f)
        lgbm_model = lgbm_bundle["model"] if isinstance(lgbm_bundle, dict) else lgbm_bundle
        lgbm_feature_cols = list(lgbm_bundle.get("feature_cols", [])) if isinstance(lgbm_bundle, dict) else []
        lgbm_threshold = float(lgbm_bundle.get("threshold", 0.5)) if isinstance(lgbm_bundle, dict) else 0.5
        lgbm_aggregation = str(lgbm_bundle.get("aggregation", "max")) if isinstance(lgbm_bundle, dict) else "max"
        if shap is not None and lgbm_model is not None:
            shap_explainer = shap.TreeExplainer(lgbm_model)
    except Exception as exc:
        print(f"[ML] WARNING: Failed to load trained artifacts ({exc}) -- using MOCK data")
        USE_MOCK = True
        gnn_model = None
        lgbm_model = None
        gnn_checkpoint = None
        gnn_scaler = None
        gnn_embedder = None
        shap_explainer = None


# ─────────────────────────────────────────────────────────
# MAIN FUNCTION -- called by the API route
# Input:  claim_data dict (already tokenized, no real PII)
# Output: FraudAnalysisResult (shape defined in schemas.py)
# ─────────────────────────────────────────────────────────
async def run_fraud_analysis(claim_data: dict) -> FraudAnalysisResult:
    if USE_MOCK:
        return _mock_analysis(claim_data)
    try:
        return await _real_analysis(claim_data)
    except NotImplementedError as exc:
        print(f"[ML] WARNING: Real model path selected but not implemented ({exc}) -- falling back to MOCK analysis")
        return _mock_analysis(claim_data)


# ─────────────────────────────────────────────────────────
# # TEAMMATE A: YOUR REAL ANALYSIS GOES IN THIS FUNCTION
# This runs ONLY when weights.pt and iforest.pkl exist
# claim_data keys: claim_token, claim_amount, claim_type,
#   incident_date, filing_date, claimant_token, provider_token,
#   repair_shop_token, prior_claim_count, days_since_last_claim
# ─────────────────────────────────────────────────────────
async def _real_analysis(claim_data: dict) -> FraudAnalysisResult:
    if not all([gnn_model, gnn_embedder, gnn_scaler, lgbm_model]):
        raise NotImplementedError("One or more trained artifacts are still unavailable at runtime.")

    nodes, edges = await get_claim_subgraph(claim_data)
    nodes = _ensure_seed_nodes(nodes, claim_data)

    if not nodes:
        raise NotImplementedError("No graph nodes could be built for the claim.")

    adjacency = build_adjacency_list(nodes, edges)
    node_ids = adjacency["node_ids"]
    claimant_token = claim_data.get("claimant_token")
    target_idx = node_ids.get(claimant_token, 0)

    node_rows = await _load_claim_history(nodes)
    raw_feature_matrix = np.vstack([
        _build_gnn_raw_features(node, claim_data, edges, node_rows.get(node.id, []))
        for node in nodes
    ]).astype(np.float32)
    scaled_features = gnn_scaler.transform(raw_feature_matrix)

    x = torch.tensor(scaled_features, dtype=torch.float32)
    edge_index = _build_edge_index(adjacency["edge_index"], len(nodes))

    with torch.no_grad():
        logits = gnn_model(x, edge_index)
        gnn_probs = torch.sigmoid(logits).cpu().numpy()
        embeddings = gnn_embedder(x, edge_index).cpu().numpy()

    target_history = node_rows.get(nodes[target_idx].id, [])
    live_prior = _live_claim_risk_prior(
        claim_data=claim_data,
        claim_rows=target_history,
        edges=edges,
        node_count=len(nodes),
    )
    gnn_score = _calibrate_gnn_score(
        raw_probability=float(gnn_probs[target_idx]),
        claim_data=claim_data,
        claim_rows=target_history,
        edges=edges,
        node_count=len(nodes),
        live_prior=live_prior,
    )
    lgbm_row = _build_lgbm_feature_row(
        claim_data=claim_data,
        target_node=nodes[target_idx],
        edges=edges,
        claim_rows=target_history,
        gnn_embedding=embeddings[target_idx],
    )
    isolation_score = _calibrate_isolation_score(
        raw_probability=_predict_lgbm_probability(lgbm_row),
        claim_data=claim_data,
        claim_rows=target_history,
        edges=edges,
        node_count=len(nodes),
        live_prior=live_prior,
    )
    graph_confidence = _graph_confidence(target_history, edges, len(nodes))
    gnn_weight = 0.18 + (0.22 * graph_confidence)
    isolation_weight = 0.52 - (0.12 * graph_confidence)
    prior_weight = 1.0 - gnn_weight - isolation_weight
    combined_score = round(
        (gnn_weight * gnn_score)
        + (isolation_weight * isolation_score)
        + (prior_weight * live_prior * 100.0),
        2,
    )
    risk_level = _risk_from_scores(combined_score, gnn_score, isolation_score)

    scored_nodes = []
    for idx, node in enumerate(nodes):
        score = _calibrate_node_score(
            raw_probability=float(gnn_probs[idx]),
            node=node,
            claim_rows=node_rows.get(node.id, []),
            edges=edges,
        )
        scored_nodes.append(
            GraphNode(
                id=node.id,
                type=node.type,
                fraud_score=score,
                claim_count=max(node.claim_count, len(node_rows.get(node.id, []))),
                is_flagged=score >= 60.0,
            )
        )

    return FraudAnalysisResult(
        gnn_score=round(gnn_score, 2),
        isolation_score=round(isolation_score, 2),
        combined_score=combined_score,
        risk_level=risk_level,
        graph_nodes=scored_nodes,
        graph_edges=edges,
        gnn_evidence=_build_gnn_evidence(nodes, edges, x, edge_index, target_idx),
        shap_features=_build_shap_features(lgbm_row),
    )


def _ensure_seed_nodes(nodes: list[GraphNode], claim_data: dict) -> list[GraphNode]:
    by_id = {node.id: node for node in nodes}
    seeds = [
        (claim_data.get("claimant_token"), "CLAIMANT"),
        (claim_data.get("provider_token"), "PROVIDER"),
        (claim_data.get("repair_shop_token"), "REPAIR_SHOP"),
    ]
    for token, node_type in seeds:
        if token and token not in by_id:
            by_id[token] = GraphNode(
                id=token,
                type=node_type,
                fraud_score=0.0,
                claim_count=0,
                is_flagged=False,
            )
    return list(by_id.values())


async def _load_claim_history(nodes: list[GraphNode]) -> dict[str, list[dict]]:
    rows_by_node: dict[str, list[dict]] = {}
    for node in nodes:
        if node.type == "CLAIMANT":
            sql = "SELECT * FROM claims WHERE claimant_token = ?"
        elif node.type == "PROVIDER":
            sql = "SELECT * FROM claims WHERE provider_token = ?"
        else:
            sql = "SELECT * FROM claims WHERE repair_shop_token = ?"
        rows_by_node[node.id] = await db.fetch_all(sql, (node.id,))
    return rows_by_node


def _build_gnn_raw_features(node: GraphNode, claim_data: dict, edges: list[GraphEdge], claim_rows: list[dict]) -> np.ndarray:
    baseline = np.array(getattr(gnn_scaler, "mean_", np.zeros(len(GNN_FEATURE_NAMES))), dtype=np.float32).copy()

    amounts = [float(row.get("claim_amount") or 0.0) for row in claim_rows if row.get("claim_amount") is not None]
    filing_lags = [_days_between(row.get("incident_date"), row.get("filing_date")) for row in claim_rows]
    filing_lags = [lag for lag in filing_lags if lag is not None]
    spacing = [
        float(row.get("days_since_last_claim") or 0.0)
        for row in claim_rows
        if row.get("days_since_last_claim") is not None
    ]

    degree = sum(1 for edge in edges if edge.source == node.id or edge.target == node.id)
    total_weight = sum(edge.weight for edge in edges if edge.source == node.id or edge.target == node.id)
    neighbors = {
        edge.target if edge.source == node.id else edge.source
        for edge in edges
        if edge.source == node.id or edge.target == node.id
    }
    primary_unique = len({
        row.get("provider_token") if node.type == "CLAIMANT"
        else row.get("claimant_token")
        for row in claim_rows
        if (row.get("provider_token") if node.type == "CLAIMANT" else row.get("claimant_token"))
    })
    secondary_unique = len({
        row.get("repair_shop_token") if node.type != "REPAIR_SHOP"
        else row.get("provider_token")
        for row in claim_rows
        if (row.get("repair_shop_token") if node.type != "REPAIR_SHOP" else row.get("provider_token"))
    })
    claim_types = len({row.get("claim_type") for row in claim_rows if row.get("claim_type")})

    base_values = {
        "log_count": math.log1p(max(len(claim_rows), 1)),
        "log_avg_amt": math.log1p(mean(amounts) if amounts else float(claim_data.get("claim_amount") or 0.0)),
        "std_amount": pstdev(amounts) if len(amounts) > 1 else 0.0,
        "max_amount": max(amounts) if amounts else float(claim_data.get("claim_amount") or 0.0),
        "unique_emails": float(primary_unique),
        "unique_devices": float(secondary_unique),
        "unique_cards": float(max(claim_types, len(neighbors), 1)),
    }
    for feature_name, value in base_values.items():
        baseline[GNN_FEATURE_INDEX[feature_name]] = float(value)

    count_signals = [
        float(len(claim_rows)),
        float(primary_unique),
        float(secondary_unique),
        float(claim_data.get("prior_claim_count") or 0),
        float(degree),
        float(total_weight),
        float(claim_types),
        float(sum(1 for row in claim_rows if (row.get("claim_amount") or 0) > 25000)),
        float(sum(1 for row in claim_rows if (row.get("claim_amount") or 0) > 45000)),
        float(len([lag for lag in filing_lags if lag <= 1])),
        float(len([space for space in spacing if space <= 45])),
        float(len(neighbors)),
        float(node.claim_count or len(claim_rows)),
        float(node.fraud_score / 10.0),
    ]
    for offset, value in enumerate(count_signals, start=1):
        baseline[GNN_FEATURE_INDEX[f"C{offset}_mean"]] = value
        baseline[GNN_FEATURE_INDEX[f"C{offset}_max"]] = value

    amount_mean = mean(amounts) if amounts else float(claim_data.get("claim_amount") or 0.0)
    delay_mean = mean(filing_lags) if filing_lags else float(_days_between(claim_data.get("incident_date"), claim_data.get("filing_date")) or 0.0)
    time_signals = [
        delay_mean,
        float(claim_data.get("days_since_last_claim") or 0.0),
        mean(spacing) if spacing else float(claim_data.get("days_since_last_claim") or 0.0),
        min(spacing) if spacing else float(claim_data.get("days_since_last_claim") or 0.0),
        max(spacing) if spacing else float(claim_data.get("days_since_last_claim") or 0.0),
        float(len([row for row in claim_rows if row.get("claim_type") == claim_data.get("claim_type")])),
        float(amount_mean),
        float(max(amounts) if amounts else amount_mean),
        float(sum((row.get("combined_score") or 0) >= 60 for row in claim_rows)),
        float(sum((row.get("combined_score") or 0) >= 80 for row in claim_rows)),
        float(sum(edge.edge_type == "treated_by" for edge in edges if edge.source == node.id or edge.target == node.id)),
        float(sum(edge.edge_type == "repaired_by" for edge in edges if edge.source == node.id or edge.target == node.id)),
        float(sum(edge.edge_type == "referred_to" for edge in edges if edge.source == node.id or edge.target == node.id)),
        float(node.claim_count or len(claim_rows)),
        float(len(neighbors)),
    ]
    for offset, value in enumerate(time_signals, start=1):
        baseline[GNN_FEATURE_INDEX[f"D{offset}_mean"]] = value
        baseline[GNN_FEATURE_INDEX[f"D{offset}_min"]] = value

    network_seed = [
        float(claim_data.get("claim_amount") or 0.0),
        float(claim_data.get("prior_claim_count") or 0.0),
        float(claim_data.get("days_since_last_claim") or 0.0),
        float(degree),
        float(total_weight),
        float(primary_unique),
        float(secondary_unique),
        float(claim_types),
        float(node.claim_count or len(claim_rows)),
        float(node.fraud_score),
    ]
    for idx, feature_name in enumerate(NETWORK_FEATURE_NAMES):
        baseline[GNN_FEATURE_INDEX[feature_name]] = network_seed[idx % len(network_seed)]

    boolean_signals = [
        1.0 if claim_data.get("repair_shop_token") else 0.0,
        1.0 if claim_data.get("claim_type") == "auto_repair" else 0.0,
        1.0 if claim_data.get("claim_type") == "medical" else 0.0,
        1.0 if (claim_data.get("prior_claim_count") or 0) > 0 else 0.0,
        1.0 if (claim_data.get("prior_claim_count") or 0) >= 3 else 0.0,
        1.0 if delay_mean <= 1 else 0.0,
        1.0 if (claim_data.get("days_since_last_claim") or 9999) <= 45 else 0.0,
        1.0 if node.is_flagged else 0.0,
        1.0 if degree >= 3 else 0.0,
    ]
    for idx, feature_name in enumerate(BOOLEAN_FEATURE_NAMES):
        baseline[GNN_FEATURE_INDEX[feature_name]] = boolean_signals[idx]

    return baseline


def _build_edge_index(edge_index_values: list[list[int]], node_count: int):
    if edge_index_values[0]:
        return torch.tensor(edge_index_values, dtype=torch.long)
    self_loops = torch.arange(node_count, dtype=torch.long)
    return torch.stack([self_loops, self_loops], dim=0)


def _build_lgbm_feature_row(
    claim_data: dict,
    target_node: GraphNode,
    edges: list[GraphEdge],
    claim_rows: list[dict],
    gnn_embedding: np.ndarray,
) -> np.ndarray:
    values = {feature_name: -999.0 for feature_name in lgbm_feature_cols}
    values["TransactionAmt"] = float(claim_data.get("claim_amount") or 0.0)

    recent_counts = float(len(claim_rows))
    filing_lag = float(_days_between(claim_data.get("incident_date"), claim_data.get("filing_date")) or 0.0)
    spacing = float(claim_data.get("days_since_last_claim") or 0.0)
    degree = float(sum(1 for edge in edges if edge.source == target_node.id or edge.target == target_node.id))
    weight = float(sum(edge.weight for edge in edges if edge.source == target_node.id or edge.target == target_node.id))

    c_values = [
        recent_counts,
        float(claim_data.get("prior_claim_count") or 0.0),
        degree,
        weight,
        float(target_node.claim_count),
        float(target_node.fraud_score),
        float(sum(edge.edge_type == "treated_by" for edge in edges)),
        float(sum(edge.edge_type == "repaired_by" for edge in edges)),
        float(sum(edge.edge_type == "referred_to" for edge in edges)),
        float(len({row.get("provider_token") for row in claim_rows if row.get("provider_token")})),
        float(len({row.get("repair_shop_token") for row in claim_rows if row.get("repair_shop_token")})),
        float(len({row.get("claim_type") for row in claim_rows if row.get("claim_type")})),
        float(sum((row.get("combined_score") or 0) >= 60 for row in claim_rows)),
        float(sum((row.get("combined_score") or 0) >= 80 for row in claim_rows)),
    ]
    d_values = [
        filing_lag,
        spacing,
        float(mean([row.get("days_since_last_claim") or 0.0 for row in claim_rows]) if claim_rows else spacing),
        float(max([row.get("days_since_last_claim") or 0.0 for row in claim_rows], default=spacing)),
        float(min([row.get("days_since_last_claim") or 0.0 for row in claim_rows], default=spacing)),
        float(sum((row.get("claim_amount") or 0) > 25000 for row in claim_rows)),
        float(sum((row.get("claim_amount") or 0) > 45000 for row in claim_rows)),
        float(mean([row.get("claim_amount") or 0.0 for row in claim_rows]) if claim_rows else values["TransactionAmt"]),
        float(max([row.get("claim_amount") or 0.0 for row in claim_rows], default=values["TransactionAmt"])),
        float(len(claim_rows)),
        degree,
        weight,
        float(target_node.claim_count),
        float(target_node.fraud_score),
        float(len(edges)),
    ]
    v_seed = [
        values["TransactionAmt"],
        float(claim_data.get("prior_claim_count") or 0.0),
        filing_lag,
        spacing,
        degree,
        weight,
        float(target_node.claim_count),
        float(target_node.fraud_score),
        float(sum(edge.weight for edge in edges)),
        recent_counts,
    ]
    m_values = [
        1.0 if claim_data.get("repair_shop_token") else 0.0,
        1.0 if claim_data.get("claim_type") == "auto_repair" else 0.0,
        1.0 if claim_data.get("claim_type") == "medical" else 0.0,
        1.0 if filing_lag <= 1 else 0.0,
        1.0 if spacing <= 45 else 0.0,
        1.0 if (claim_data.get("prior_claim_count") or 0) >= 1 else 0.0,
        1.0 if (claim_data.get("prior_claim_count") or 0) >= 3 else 0.0,
        1.0 if degree >= 3 else 0.0,
        1.0 if values["TransactionAmt"] >= 25000 else 0.0,
    ]

    for idx, value in enumerate(c_values, start=1):
        for suffix in ("mean", "max"):
            feature_name = f"C{idx}_{suffix}"
            if feature_name in values:
                values[feature_name] = value
    for idx, value in enumerate(d_values, start=1):
        for suffix in ("mean", "min"):
            feature_name = f"D{idx}_{suffix}"
            if feature_name in values:
                values[feature_name] = value
    for idx in range(1, 51):
        feature_name = f"V{idx}"
        if feature_name in values:
            values[feature_name] = v_seed[(idx - 1) % len(v_seed)]
    for idx in range(1, 10):
        feature_name = f"M{idx}"
        if feature_name in values:
            values[feature_name] = m_values[idx - 1]
    for idx in range(min(20, len(gnn_embedding))):
        feature_name = f"gnn_emb_{idx}"
        if feature_name in values:
            values[feature_name] = float(gnn_embedding[idx])

    return pd.DataFrame([[values[name] for name in lgbm_feature_cols]], columns=lgbm_feature_cols, dtype=np.float32)


def _predict_lgbm_probability(row: pd.DataFrame) -> float:
    if hasattr(lgbm_model, "predict_proba"):
        return float(lgbm_model.predict_proba(row)[0, 1])
    if isinstance(lgbm_model, Booster):
        return float(lgbm_model.predict(row)[0])
    return float(lgbm_model.predict(row)[0])


def _build_shap_features(row: pd.DataFrame) -> list[SHAPFeature]:
    if shap_explainer is None or not lgbm_feature_cols:
        return []

    shap_values = shap_explainer.shap_values(row)
    if isinstance(shap_values, list):
        contributions = np.array(shap_values[-1][0], dtype=float)
    else:
        contributions = np.array(shap_values[0], dtype=float)

    total = float(np.abs(contributions).sum()) or 1.0
    top_indices = np.argsort(np.abs(contributions))[::-1][:5]
    features = []
    for idx in top_indices:
        contribution = float(abs(contributions[idx]) / total)
        features.append(
            SHAPFeature(
                feature_name=lgbm_feature_cols[idx],
                value=float(row.iloc[0, idx]),
                contribution=min(contribution, 1.0),
                direction="increases_risk" if contributions[idx] >= 0 else "decreases_risk",
            )
        )
    return features


def _build_gnn_evidence(
    nodes: list[GraphNode],
    edges: list[GraphEdge],
    x,
    edge_index,
    target_idx: int,
) -> list[GNNEvidence]:
    if not edges:
        return []

    node_lookup = {node.id: node for node in nodes}
    edge_scores = np.ones(len(edges), dtype=float)
    if ENABLE_GNN_EXPLAINER and Explainer is not None and GNNExplainer is not None and len(edges) <= 12 and len(nodes) <= 8:
        try:
            class ProbabilityWrapper(torch.nn.Module):
                def __init__(self, inner_model):
                    super().__init__()
                    self.inner_model = inner_model

                def forward(self, feats, graph_edges):
                    return torch.sigmoid(self.inner_model(feats, graph_edges))

            explainer = Explainer(
                model=ProbabilityWrapper(gnn_model),
                algorithm=GNNExplainer(epochs=50),
                explanation_type="model",
                node_mask_type="attributes",
                edge_mask_type="object",
                model_config={
                    "mode": "binary_classification",
                    "task_level": "node",
                    "return_type": "probs",
                },
            )
            explanation = explainer(x, edge_index, index=target_idx)
            mask = explanation.edge_mask.detach().cpu().numpy()
            undirected_mask = mask[::2] if len(mask) >= len(edges) * 2 else mask[:len(edges)]
            if len(undirected_mask) == len(edges):
                edge_scores = undirected_mask
        except Exception as exc:
            print(f"[ML] WARNING: GNNExplainer failed ({exc}) -- using graph fallback evidence")
            edge_scores = np.array([
                _heuristic_edge_score(edge, nodes[target_idx].id, node_lookup)
                for edge in edges
            ], dtype=float)
    else:
        edge_scores = np.array([
            _heuristic_edge_score(edge, nodes[target_idx].id, node_lookup)
            for edge in edges
        ], dtype=float)

    connected = []
    target_token = nodes[target_idx].id
    max_score = float(np.max(edge_scores)) or 1.0
    for idx, edge in enumerate(edges):
        if edge.source != target_token and edge.target != target_token:
            continue
        other_token = edge.target if edge.source == target_token else edge.source
        other_node = node_lookup.get(other_token)
        label = _human_edge_label(edge, other_node)
        connected.append(
            GNNEvidence(
                source_token=edge.source,
                target_token=edge.target,
                edge_type=edge.edge_type,
                importance_score=min(float(edge_scores[idx] / max_score), 1.0),
                human_label=label,
            )
        )
    return sorted(connected, key=lambda item: item.importance_score, reverse=True)[:5]


def _human_edge_label(edge: GraphEdge, neighbor: GraphNode | None) -> str:
    neighbor_type = neighbor.type.replace("_", " ").lower() if neighbor else "linked entity"
    neighbor_claims = neighbor.claim_count if neighbor else edge.weight
    if edge.edge_type == "repaired_by":
        return f"Claim shares repair relationship with a {neighbor_type} seen in {neighbor_claims} claims"
    if edge.edge_type == "treated_by":
        return f"Claim shares provider relationship with a {neighbor_type} seen in {neighbor_claims} claims"
    if edge.edge_type == "referred_to":
        return f"Provider and shop form a referral path reused across {neighbor_claims} claims"
    if edge.edge_type == "shared_incident":
        return "Claim is connected to another entity through a shared incident pattern"
    return "Graph relationship materially increases the claimant risk score"


def _heuristic_edge_score(edge: GraphEdge, target_token: str, node_lookup: dict[str, GraphNode]) -> float:
    other_token = edge.target if edge.source == target_token else edge.source
    other_node = node_lookup.get(other_token)
    support = min(float((other_node.claim_count if other_node else edge.weight) or 0) / 6.0, 1.0)
    edge_bias = {
        "referred_to": 0.92,
        "repaired_by": 0.88,
        "shared_incident": 0.82,
        "treated_by": 0.72,
    }.get(edge.edge_type, 0.65)
    return min(1.0, edge_bias + (0.18 * support))


def _days_between(start: str | None, end: str | None) -> int | None:
    if not start or not end:
        return None
    try:
        return abs((np.datetime64(end) - np.datetime64(start)).astype("timedelta64[D]").astype(int))
    except Exception:
        return None


def _risk_from_scores(combined_score: float, gnn_score: float, isolation_score: float) -> str:
    if combined_score >= 88 or (gnn_score >= 85 and isolation_score >= 78):
        return "CRITICAL"
    if combined_score >= 67 or max(gnn_score, isolation_score) >= 82:
        return "HIGH"
    if combined_score >= 42:
        return "MEDIUM"
    return "LOW"


def _live_claim_risk_prior(
    claim_data: dict,
    claim_rows: list[dict],
    edges: list[GraphEdge],
    node_count: int,
) -> float:
    amount = float(claim_data.get("claim_amount") or 0.0)
    prior_claims = float(claim_data.get("prior_claim_count") or 0.0)
    days_since_last = float(claim_data.get("days_since_last_claim") or 0.0)
    filing_lag = float(_days_between(claim_data.get("incident_date"), claim_data.get("filing_date")) or 0.0)
    claim_type = str(claim_data.get("claim_type") or "").lower()
    has_shop = 1.0 if claim_data.get("repair_shop_token") else 0.0
    degree = sum(
        1 for edge in edges
        if edge.source == claim_data.get("claimant_token") or edge.target == claim_data.get("claimant_token")
    )

    amount_ratio = min(amount / 50000.0, 1.0)
    prior_ratio = min(prior_claims / 4.0, 1.0)
    recency_ratio = 1.0 if 0.0 < days_since_last <= 14 else 0.75 if days_since_last <= 45 else 0.0
    filing_ratio = 1.0 if filing_lag <= 1 else 0.45 if filing_lag <= 3 else 0.0
    history_ratio = min(max(len(claim_rows) - 1, 0) / 4.0, 1.0)
    graph_ratio = min((degree + max(node_count - 1, 0)) / 7.0, 1.0)
    claim_type_ratio = 1.0 if claim_type == "auto_repair" else 0.55 if claim_type == "medical" else 0.2

    prior = (
        0.28 * amount_ratio
        + 0.26 * prior_ratio
        + 0.14 * recency_ratio
        + 0.08 * filing_ratio
        + 0.12 * history_ratio
        + 0.07 * graph_ratio
        + 0.05 * claim_type_ratio
    )

    if has_shop and claim_type == "auto_repair":
        prior += 0.05
    if amount >= 40000:
        prior += 0.07
    elif amount >= 25000:
        prior += 0.04
    if prior_claims >= 3:
        prior += 0.09
    elif prior_claims >= 1:
        prior += 0.03

    return max(0.0, min(prior, 1.0))


def _calibrate_gnn_score(
    raw_probability: float,
    claim_data: dict,
    claim_rows: list[dict],
    edges: list[GraphEdge],
    node_count: int,
    live_prior: float | None = None,
) -> float:
    degree = sum(1 for edge in edges if edge.source == claim_data.get("claimant_token") or edge.target == claim_data.get("claimant_token"))
    live_prior = live_prior if live_prior is not None else _live_claim_risk_prior(
        claim_data=claim_data,
        claim_rows=claim_rows,
        edges=edges,
        node_count=node_count,
    )
    graph_ratio = min((degree + max(node_count - 1, 0)) / 7.0, 1.0)

    calibrated = (0.42 * raw_probability) + (0.48 * live_prior) + (0.10 * graph_ratio)
    if live_prior >= 0.72 and raw_probability >= 0.20:
        calibrated += 0.12
    if len(claim_rows) <= 1 and degree <= 2 and live_prior < 0.45:
        calibrated *= 0.72
    return round(max(0.0, min(calibrated, 1.0)) * 100.0, 2)


def _calibrate_isolation_score(
    raw_probability: float,
    claim_data: dict,
    claim_rows: list[dict],
    edges: list[GraphEdge],
    node_count: int,
    live_prior: float | None = None,
) -> float:
    live_prior = live_prior if live_prior is not None else _live_claim_risk_prior(
        claim_data=claim_data,
        claim_rows=claim_rows,
        edges=edges,
        node_count=node_count,
    )
    history_ratio = min(max(len(claim_rows) - 1, 0) / 4.0, 1.0)
    calibrated = max(
        (0.30 * raw_probability) + (0.70 * live_prior),
        (0.62 * live_prior) + (0.18 * history_ratio),
    )
    if len(claim_rows) <= 1 and live_prior < 0.35:
        calibrated *= 0.70
    return round(max(0.0, min(calibrated, 1.0)) * 100.0, 2)


def _calibrate_node_score(
    raw_probability: float,
    node: GraphNode,
    claim_rows: list[dict],
    edges: list[GraphEdge],
) -> float:
    degree = sum(1 for edge in edges if edge.source == node.id or edge.target == node.id)
    support = min((len(claim_rows) + degree) / 6.0, 1.0)
    calibrated = (0.65 * raw_probability) + (0.35 * support * raw_probability)
    if len(claim_rows) <= 1 and degree <= 2:
        calibrated *= 0.75
    return round(max(0.0, min(calibrated, 1.0)) * 100.0, 2)


def _graph_confidence(claim_rows: list[dict], edges: list[GraphEdge], node_count: int) -> float:
    return min((len(claim_rows) + len(edges) + max(node_count - 1, 0)) / 10.0, 1.0)


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
