import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.schemas import GraphEdge, GraphNode
from services.ml_interface import (
    _calibrate_gnn_score,
    _calibrate_isolation_score,
    _heuristic_edge_score,
    _live_claim_risk_prior,
    _risk_from_scores,
)


class MlRuntimeCalibrationTests(unittest.TestCase):
    def setUp(self):
        self.clean_claim = {
            "claimant_token": "CLAIMANT_CLEAN",
            "provider_token": "PROVIDER_CLEAN",
            "repair_shop_token": "",
            "claim_amount": 1800,
            "claim_type": "property",
            "incident_date": "2024-06-01",
            "filing_date": "2024-06-04",
            "prior_claim_count": 0,
            "days_since_last_claim": 400,
        }
        self.high_risk_claim = {
            "claimant_token": "CLAIMANT_REPEAT",
            "provider_token": "PROVIDER_REPEAT",
            "repair_shop_token": "SHOP_REPEAT",
            "claim_amount": 49500,
            "claim_type": "auto_repair",
            "incident_date": "2024-04-20",
            "filing_date": "2024-04-21",
            "prior_claim_count": 4,
            "days_since_last_claim": 10,
        }
        self.clean_rows = [dict(self.clean_claim, combined_score=0)]
        self.high_risk_rows = [
            dict(self.high_risk_claim, claim_amount=28000, combined_score=74),
            dict(self.high_risk_claim, claim_amount=41000, combined_score=88),
            dict(self.high_risk_claim, claim_amount=36500, combined_score=81),
        ]
        self.clean_edges = [
            GraphEdge(source="CLAIMANT_CLEAN", target="PROVIDER_CLEAN", weight=1, edge_type="treated_by", timestamp="2024-06-04"),
        ]
        self.high_risk_edges = [
            GraphEdge(source="CLAIMANT_REPEAT", target="PROVIDER_REPEAT", weight=3, edge_type="treated_by", timestamp="2024-04-21"),
            GraphEdge(source="CLAIMANT_REPEAT", target="SHOP_REPEAT", weight=3, edge_type="repaired_by", timestamp="2024-04-21"),
            GraphEdge(source="PROVIDER_REPEAT", target="SHOP_REPEAT", weight=3, edge_type="referred_to", timestamp="2024-04-21"),
        ]

    def test_live_prior_ranks_repeat_auto_claim_above_clean_property(self):
        clean_prior = _live_claim_risk_prior(self.clean_claim, self.clean_rows, self.clean_edges, 2)
        high_prior = _live_claim_risk_prior(self.high_risk_claim, self.high_risk_rows, self.high_risk_edges, 3)

        self.assertLess(clean_prior, 0.25)
        self.assertGreater(high_prior, 0.75)

    def test_calibrated_scores_preserve_expected_ordering(self):
        clean_prior = _live_claim_risk_prior(self.clean_claim, self.clean_rows, self.clean_edges, 2)
        high_prior = _live_claim_risk_prior(self.high_risk_claim, self.high_risk_rows, self.high_risk_edges, 3)

        clean_gnn = _calibrate_gnn_score(0.22, self.clean_claim, self.clean_rows, self.clean_edges, 2, clean_prior)
        high_gnn = _calibrate_gnn_score(0.28, self.high_risk_claim, self.high_risk_rows, self.high_risk_edges, 3, high_prior)
        clean_iso = _calibrate_isolation_score(0.18, self.clean_claim, self.clean_rows, self.clean_edges, 2, clean_prior)
        high_iso = _calibrate_isolation_score(0.24, self.high_risk_claim, self.high_risk_rows, self.high_risk_edges, 3, high_prior)

        self.assertLess(clean_gnn, 35.0)
        self.assertGreater(high_gnn, 65.0)
        self.assertLess(clean_iso, 30.0)
        self.assertGreater(high_iso, 70.0)

    def test_risk_bands_match_thresholds(self):
        self.assertEqual(_risk_from_scores(18.0, 20.0, 16.0), "LOW")
        self.assertEqual(_risk_from_scores(50.0, 44.0, 53.0), "MEDIUM")
        self.assertEqual(_risk_from_scores(72.0, 60.0, 75.0), "HIGH")
        self.assertEqual(_risk_from_scores(90.0, 87.0, 80.0), "CRITICAL")

    def test_referred_edges_rank_above_basic_provider_links(self):
        node_lookup = {
            "PROVIDER_REPEAT": GraphNode(id="PROVIDER_REPEAT", type="PROVIDER", fraud_score=0.0, claim_count=6, is_flagged=False),
            "SHOP_REPEAT": GraphNode(id="SHOP_REPEAT", type="REPAIR_SHOP", fraud_score=0.0, claim_count=8, is_flagged=True),
        }
        treated = _heuristic_edge_score(
            GraphEdge(source="CLAIMANT_REPEAT", target="PROVIDER_REPEAT", weight=1, edge_type="treated_by", timestamp="2024-04-21"),
            "CLAIMANT_REPEAT",
            node_lookup,
        )
        referred = _heuristic_edge_score(
            GraphEdge(source="CLAIMANT_REPEAT", target="SHOP_REPEAT", weight=1, edge_type="repaired_by", timestamp="2024-04-21"),
            "CLAIMANT_REPEAT",
            node_lookup,
        )

        self.assertGreater(referred, treated)


if __name__ == "__main__":
    unittest.main()
