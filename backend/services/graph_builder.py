"""
Graph construction helpers for Teammate A.
These functions turn database records into graph structures
suitable for PyTorch Geometric / DGL.

Teammate A: import from here inside _real_analysis() in ml_interface.py
"""

from typing import List, Tuple
from models.schemas import GraphNode, GraphEdge
from core import database as db


async def get_entity_neighbors(entity_token: str, depth: int = 2) -> Tuple[List[GraphNode], List[GraphEdge]]:
    """
    Fetch the neighborhood graph around a given entity token.
    Returns (nodes, edges) up to `depth` hops away.
    Currently uses SQLite; when Teammate B connects Db2, same query works.
    """
    # Get all edges involving this entity (1-hop)
    rows = await db.fetch_all(
        """SELECT source, target, edge_type, weight, timestamp
           FROM graph_edges
           WHERE source = ? OR target = ?""",
        (entity_token, entity_token),
    )

    if not rows:
        return [], []

    # Collect all unique entity tokens seen
    tokens = {entity_token}
    edges = []
    for row in rows:
        tokens.add(row["source"])
        tokens.add(row["target"])
        edges.append(GraphEdge(
            source    = row["source"],
            target    = row["target"],
            edge_type = row["edge_type"],
            weight    = row["weight"],
            timestamp = row["timestamp"],
        ))

    # Fetch entity details for all tokens
    nodes = []
    for token in tokens:
        entity = await db.fetch_one(
            "SELECT entity_token, entity_type, fraud_score, claim_count, is_flagged FROM entities WHERE entity_token = ?",
            (token,)
        )
        if entity:
            nodes.append(GraphNode(
                id          = entity["entity_token"],
                type        = entity["entity_type"],
                fraud_score = entity["fraud_score"],
                claim_count = entity["claim_count"],
                is_flagged  = bool(entity["is_flagged"]),
            ))

    return nodes, edges


def build_adjacency_list(nodes: List[GraphNode], edges: List[GraphEdge]) -> dict:
    """
    Returns an adjacency list dict for use with PyG or NetworkX.
    Format: {node_id: [neighbor_id, ...]}

    Teammate A: use this to build your edge_index tensor.
    """
    node_ids = {n.id: i for i, n in enumerate(nodes)}
    adj = {n.id: [] for n in nodes}
    edge_index = [[], []]  # [source_indices, target_indices]

    for edge in edges:
        if edge.source in adj and edge.target in adj:
            adj[edge.source].append(edge.target)
            adj[edge.target].append(edge.source)  # undirected
            src_idx = node_ids[edge.source]
            tgt_idx = node_ids[edge.target]
            edge_index[0].extend([src_idx, tgt_idx])
            edge_index[1].extend([tgt_idx, src_idx])

    return {
        "adjacency": adj,
        "edge_index": edge_index,   # ready for torch.tensor(edge_index, dtype=torch.long)
        "node_ids": node_ids,       # {token: idx} mapping
    }


def build_node_features(nodes: List[GraphNode]) -> List[List[float]]:
    """
    Build a feature matrix [N, F] where:
    F0 = claim_count (normalized by 20)
    F1 = fraud_score (normalized by 100)
    F2 = is_flagged (binary)
    F3 = is_claimant (binary)
    F4 = is_provider (binary)
    F5 = is_repair_shop (binary)

    Teammate A: convert this to torch.FloatTensor for GNN input.
    """
    features = []
    for node in nodes:
        features.append([
            min(node.claim_count / 20.0, 1.0),     # F0
            node.fraud_score / 100.0,               # F1
            1.0 if node.is_flagged else 0.0,        # F2
            1.0 if node.type == "CLAIMANT" else 0.0,    # F3
            1.0 if node.type == "PROVIDER" else 0.0,    # F4
            1.0 if node.type == "REPAIR_SHOP" else 0.0, # F5
        ])
    return features


async def store_graph_edges(edges: List[GraphEdge]) -> None:
    """Persist graph edges to the database (for history + replay)."""
    if not edges:
        return
    await db.execute_many(
        "INSERT OR IGNORE INTO graph_edges (source, target, edge_type, weight, timestamp) VALUES (?,?,?,?,?)",
        [(e.source, e.target, e.edge_type, e.weight, e.timestamp) for e in edges],
    )
