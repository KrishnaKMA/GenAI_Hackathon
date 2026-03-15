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


async def get_claim_subgraph(claim_data: dict) -> Tuple[List[GraphNode], List[GraphEdge]]:
    """
    Build the local graph neighborhood relevant to a single claim by merging
    the claimant/provider/shop neighborhoods already stored in the database.
    """
    seed_tokens = [
        claim_data.get("claimant_token"),
        claim_data.get("provider_token"),
        claim_data.get("repair_shop_token"),
    ]
    seed_tokens = [token for token in seed_tokens if token]

    merged_nodes: dict[str, GraphNode] = {}
    merged_edges: dict[tuple[str, str, str, str], GraphEdge] = {}

    for token in seed_tokens:
        nodes, edges = await get_entity_neighbors(token)
        for node in nodes:
            merged_nodes[node.id] = node
        for edge in edges:
            key = (edge.source, edge.target, edge.edge_type, edge.timestamp)
            merged_edges[key] = edge

    # Guarantee the current claim's primary relationship edges are present even
    # if this is the first time the entities appear in the graph.
    timestamp = claim_data.get("incident_date") or claim_data.get("filing_date") or ""
    claimant = claim_data.get("claimant_token")
    provider = claim_data.get("provider_token")
    shop = claim_data.get("repair_shop_token")

    if claimant and provider:
        merged_edges.setdefault(
            (claimant, provider, "treated_by", timestamp),
            GraphEdge(
                source=claimant,
                target=provider,
                edge_type="treated_by",
                weight=1,
                timestamp=timestamp,
            ),
        )
    if claimant and shop:
        merged_edges.setdefault(
            (claimant, shop, "repaired_by", timestamp),
            GraphEdge(
                source=claimant,
                target=shop,
                edge_type="repaired_by",
                weight=1,
                timestamp=timestamp,
            ),
        )
    if provider and shop:
        merged_edges.setdefault(
            (provider, shop, "referred_to", timestamp),
            GraphEdge(
                source=provider,
                target=shop,
                edge_type="referred_to",
                weight=1,
                timestamp=timestamp,
            ),
        )

    return list(merged_nodes.values()), list(merged_edges.values())


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

    where_clauses = []
    params: list[str] = []
    for edge in edges:
        where_clauses.append("(source = ? AND target = ? AND edge_type = ? AND timestamp = ?)")
        params.extend([edge.source, edge.target, edge.edge_type, edge.timestamp])

    existing_rows = await db.fetch_all(
        f"SELECT source, target, edge_type, timestamp FROM graph_edges WHERE {' OR '.join(where_clauses)}",
        tuple(params),
    )
    existing_keys = {
        (row["source"], row["target"], row["edge_type"], row["timestamp"])
        for row in existing_rows
    }
    new_edges = [
        (e.source, e.target, e.edge_type, e.weight, e.timestamp)
        for e in edges
        if (e.source, e.target, e.edge_type, e.timestamp) not in existing_keys
    ]
    if new_edges:
        await db.execute_many(
            "INSERT INTO graph_edges (source, target, edge_type, weight, timestamp) VALUES (?,?,?,?,?)",
            new_edges,
        )


async def update_entity_scores(nodes: List[GraphNode]) -> None:
    """
    Persist model feedback onto entity rows so future graph lookups reflect the
    latest fraud scores and flags.
    """
    if not nodes:
        return

    for node in nodes:
        await db.execute(
            """UPDATE entities
               SET fraud_score = ?, is_flagged = ?, claim_count = ?, last_seen = CURRENT_TIMESTAMP
               WHERE entity_token = ?""",
            (
                node.fraud_score,
                1 if node.is_flagged else 0,
                node.claim_count,
                node.id,
            ),
        )
