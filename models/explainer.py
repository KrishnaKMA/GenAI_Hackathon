# Explainability — SHAP + GNNExplainer
import subprocess, sys
subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "shap"])
import shap
from torch_geometric.explain import Explainer, GNNExplainer

print("Building explainability layer …")

# SHAP for LightGBM
print("\n[1/2] SHAP feature attribution for LightGBM …")

# use a sample of test transactions for speed
sample_size = 500
np.random.seed(SEED)
sample_idx  = np.random.choice(len(X_te), sample_size, replace=False)
X_sample    = X_te[sample_idx]

explainer_shap = shap.TreeExplainer(lgbm_model)
shap_values    = explainer_shap.shap_values(X_sample)

# shap_values is list [class0, class1] for binary — take class 1 (fraud)
sv = shap_values[1] if isinstance(shap_values, list) else shap_values

# top 15 most important features by mean absolute SHAP
mean_abs_shap  = np.abs(sv).mean(axis=0)
top15_idx      = mean_abs_shap.argsort()[::-1][:15]
top15_features = [(lgbm_tx_features[i], mean_abs_shap[i]) for i in top15_idx]

print("  Top 15 features by mean |SHAP|:")
for feat, importance in top15_features:
    bar = "█" * int(importance * 200)
    print(f"    {feat:<20} {importance:.4f}  {bar}")

# per-card SHAP explanation helper
def explain_card(card_id: int, top_n: int = 10) -> dict:
    """Return top-N SHAP features driving fraud score for a given card."""
    if card_id not in card2idx:
        return {"error": "card not in training data"}

    # get transactions for this card
    card_txs = df_tx[df_tx["card1"] == card_id][lgbm_tx_features].fillna(-999)
    if len(card_txs) == 0:
        return {"error": "no transactions found"}

    X_card    = card_txs.values.astype(np.float32)
    sv_card   = explainer_shap.shap_values(X_card)
    sv_card   = sv_card[1] if isinstance(sv_card, list) else sv_card

    # aggregate: mean SHAP across all transactions for this card
    mean_sv   = sv_card.mean(axis=0)
    top_idx   = np.abs(mean_sv).argsort()[::-1][:top_n]

    return {
        "card_id":      card_id,
        "fraud_prob":   float(lgbm_model.predict_proba(X_card)[:, 1].max()),
        "top_features": [
            {
                "feature":    lgbm_tx_features[i],
                "shap_value": round(float(mean_sv[i]), 4),
                "direction":  "↑ fraud" if mean_sv[i] > 0 else "↓ fraud",
            }
            for i in top_idx
        ],
    }

# save SHAP explainer
with open(f"{OUT_DIR}/gnn/shap_explainer.pkl", "wb") as fh:
    pickle.dump({
        "explainer":      explainer_shap,
        "feature_cols":   lgbm_tx_features,
        "top15_features": top15_features,
    }, fh)
print(f"  Saved → {OUT_DIR}/gnn/shap_explainer.pkl")

# GNNExplainer for subgraph attribution
print("\n[2/2] GNNExplainer subgraph attribution …")

# GNNExplainer needs model in train mode with gradients
explainer_gnn = Explainer(
    model=model,
    algorithm=GNNExplainer(epochs=200),
    explanation_type="model",
    node_mask_type="attributes",
    edge_mask_type="object",
    model_config=dict(
        mode="binary_classification",
        task_level="node",
        return_type="probs",
    ),
)

def explain_node(node_idx: int) -> dict:
    """
    Return edge importances and feature attributions for a given node.
    Used to identify which neighbors most contribute to fraud score.
    """
    explanation = explainer_gnn(
        data.x, data.edge_index, index=node_idx
    )

    # top contributing edges (neighbor nodes)
    edge_mask    = explanation.edge_mask.cpu().numpy()
    edge_index_np = data.edge_index.cpu().numpy()

    # get edges connected to this node
    node_edges   = np.where(
        (edge_index_np[0] == node_idx) | (edge_index_np[1] == node_idx)
    )[0]
    neighbor_importance = sorted(
        [
            {
                "neighbor_idx": int(edge_index_np[1, e] if edge_index_np[0, e] == node_idx
                                    else edge_index_np[0, e]),
                "edge_weight":  round(float(edge_mask[e]), 4),
            }
            for e in node_edges
        ],
        key=lambda x: x["edge_weight"], reverse=True
    )[:5]  # top 5 neighbors

    # top contributing node features
    feat_mask   = explanation.node_feat_mask.cpu().numpy()[0]
    top_feat_idx = np.abs(feat_mask).argsort()[::-1][:10]
    feature_importance = [
        {
            "feature":    NODE_FEATURE_COLS[i],
            "importance": round(float(feat_mask[i]), 4),
        }
        for i in top_feat_idx
    ]

    return {
        "node_idx":            node_idx,
        "fraud_prob":          float(torch.sigmoid(
                                   model(data.x, data.edge_index)[node_idx]
                               ).item()),
        "top_neighbors":       neighbor_importance,
        "top_features":        feature_importance,
    }

# run GNNExplainer on a sample of high-risk test nodes for verification
model.eval()
with torch.no_grad():
    all_logits = model(data.x, data.edge_index)
    all_probs  = torch.sigmoid(all_logits).cpu().numpy()

te_indices     = np.where(test_mask.cpu().numpy())[0]
high_risk_idx  = te_indices[all_probs[te_indices].argsort()[::-1][:3]]

print("  GNNExplainer on top-3 highest risk test nodes:")
gnn_explanations = []
for nidx in high_risk_idx:
    try:
        exp = explain_node(int(nidx))
        gnn_explanations.append(exp)
        print(f"\n  Node {nidx}  fraud_prob={exp['fraud_prob']:.4f}")
        print(f"    Top neighbors: {[n['neighbor_idx'] for n in exp['top_neighbors']]}")
        print(f"    Top features : {[f['feature'] for f in exp['top_features'][:3]]}")
    except Exception as e:
        print(f"  Node {nidx} failed: {e}")

# save GNN explanations
with open(f"{OUT_DIR}/gnn/gnn_explanations_sample.pkl", "wb") as fh:
    pickle.dump(gnn_explanations, fh)
print(f"\n  Saved → {OUT_DIR}/gnn/gnn_explanations_sample.pkl")

# Summary
print("\n" + "="*60)
print("EXPLAINABILITY COMPLETE")
print("="*60)
print(f"  SHAP explainer    : {OUT_DIR}/gnn/shap_explainer.pkl")
print(f"  GNN explanations  : {OUT_DIR}/gnn/gnn_explanations_sample.pkl")
print(f"  explain_card()    : call with any card_id for SHAP breakdown")
print(f"  explain_node()    : call with any node_idx for subgraph attribution")
print("="*60)