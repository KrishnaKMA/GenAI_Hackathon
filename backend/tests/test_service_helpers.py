import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.schemas import ClaimRecord, GraphEdge, GraphNode
from services.claim_ingestor import _build_claim_edges, build_claim_data_dict
from services.graph_builder import build_adjacency_list, build_node_features


class ClaimHelperTests(unittest.TestCase):
    def test_build_claim_edges_without_repair_shop(self):
        record = ClaimRecord(
            claim_token="CLAIM_X",
            claim_amount=1250.0,
            claim_type="medical",
            incident_date="2024-01-01",
            filing_date="2024-01-02",
            prior_claim_count=0,
            days_since_last_claim=None,
            claimant_token="CLAIMANT_A",
            provider_token="PROVIDER_A",
            repair_shop_token=None,
            adjuster_id="adjuster1",
        )

        edges = _build_claim_edges(record)

        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0].edge_type, "treated_by")
        self.assertEqual(edges[0].source, "CLAIMANT_A")
        self.assertEqual(edges[0].target, "PROVIDER_A")

    def test_build_claim_edges_with_repair_shop(self):
        record = ClaimRecord(
            claim_token="CLAIM_Y",
            claim_amount=45000.0,
            claim_type="auto_repair",
            incident_date="2024-02-01",
            filing_date="2024-02-03",
            prior_claim_count=3,
            days_since_last_claim=21,
            claimant_token="CLAIMANT_B",
            provider_token="PROVIDER_B",
            repair_shop_token="SHOP_B",
            adjuster_id="adjuster1",
        )

        edges = _build_claim_edges(record)
        edge_types = {edge.edge_type for edge in edges}

        self.assertEqual(len(edges), 3)
        self.assertEqual(edge_types, {"treated_by", "repaired_by", "referred_to"})

    def test_build_claim_data_dict_defaults(self):
        record = ClaimRecord(
            claim_token="CLAIM_Z",
            claim_amount=900.0,
            claim_type="property",
            incident_date="2024-03-01",
            filing_date="2024-03-05",
            prior_claim_count=0,
            days_since_last_claim=None,
            claimant_token="CLAIMANT_C",
            provider_token="PROVIDER_C",
            repair_shop_token=None,
            adjuster_id="adjuster1",
        )

        payload = build_claim_data_dict(record)

        self.assertEqual(payload["repair_shop_token"], "")
        self.assertEqual(payload["days_since_last_claim"], 0)


class GraphHelperTests(unittest.TestCase):
    def test_build_adjacency_list_ignores_unknown_edge(self):
        nodes = [
            GraphNode(id="CLAIMANT_A", type="CLAIMANT", fraud_score=0.0, claim_count=1, is_flagged=False),
            GraphNode(id="PROVIDER_A", type="PROVIDER", fraud_score=0.0, claim_count=2, is_flagged=False),
        ]
        edges = [
            GraphEdge(source="CLAIMANT_A", target="PROVIDER_A", weight=1, edge_type="treated_by", timestamp="2024-01-01"),
            GraphEdge(source="CLAIMANT_A", target="MISSING_NODE", weight=1, edge_type="treated_by", timestamp="2024-01-01"),
        ]

        adjacency = build_adjacency_list(nodes, edges)

        self.assertEqual(adjacency["adjacency"]["CLAIMANT_A"], ["PROVIDER_A"])
        self.assertEqual(adjacency["adjacency"]["PROVIDER_A"], ["CLAIMANT_A"])
        self.assertEqual(len(adjacency["edge_index"][0]), 2)

    def test_build_node_features_shape_and_flags(self):
        nodes = [
            GraphNode(id="CLAIMANT_A", type="CLAIMANT", fraud_score=80.0, claim_count=3, is_flagged=True),
            GraphNode(id="SHOP_A", type="REPAIR_SHOP", fraud_score=15.0, claim_count=1, is_flagged=False),
        ]

        matrix = build_node_features(nodes)

        self.assertEqual(len(matrix), 2)
        self.assertEqual(len(matrix[0]), 6)
        self.assertEqual(matrix[0][2], 1.0)
        self.assertEqual(matrix[0][3], 1.0)
        self.assertEqual(matrix[1][5], 1.0)


if __name__ == "__main__":
    unittest.main()
