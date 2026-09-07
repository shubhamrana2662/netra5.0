"""
CyberDrishti AI — Graph Engine Unit Tests
==========================================
Run tests:
    python -m unittest tests/test_graph_engine.py
"""

from __future__ import annotations

import sys
import unittest
import tempfile
import pathlib
import networkx as nx
import numpy as np

# Ensure graph_engine root directory is in sys.path when tests are run from repository root
_ENGINE_DIR = pathlib.Path(__file__).resolve().parent.parent
if str(_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(_ENGINE_DIR))

from core.canonicalizer import UnionFind, canonicalise_entities, similarity
from core.extractors import RegexExtractor
from core.builder import build_case_graph, graph_to_json
from core.hidden_link_engine import (
    HiddenLinkEngine,
    common_neighbors,
    jaccard,
    adamic_adar,
    preferential_attachment,
    temporal_co_occurrence,
    financial_correlation,
    compute_pair_features,
)
from core.serializer import serialize_graph_for_visualization
from visualizer import generate_interactive_html


class TestUnionFind(unittest.TestCase):
    def test_find_and_union(self):
        uf = UnionFind()
        uf.find("a")
        uf.find("b")
        uf.find("c")
        self.assertNotEqual(uf.find("a"), uf.find("b"))
        uf.union("a", "b")
        self.assertEqual(uf.find("a"), uf.find("b"))
        uf.union("b", "c")
        self.assertEqual(uf.find("a"), uf.find("c"))
        groups = uf.groups()
        self.assertEqual(len(groups), 1)


class TestCanonicalizer(unittest.TestCase):
    def test_hard_id_preservation(self):
        # Even if two phone numbers differ by only 1 digit, they must NEVER merge
        sim = similarity("+919876543210", "+919876543211", "PHONE")
        self.assertEqual(sim, 0.0)

        # Exact match
        sim_exact = similarity("+919876543210", "+919876543210", "PHONE")
        self.assertEqual(sim_exact, 1.0)

    def test_fuzzy_name_merging(self):
        mentions = [
            {"raw_value": "Vikram Sharma", "entity_type": "PER"},
            {"raw_value": "Sharma, Vikram", "entity_type": "PER"},
            {"raw_value": "Sanjeev Kumar", "entity_type": "PER"},
        ]
        groups = canonicalise_entities(mentions)
        # Vikram Sharma and Sharma, Vikram should merge into one cluster
        self.assertEqual(len(groups), 2)


class TestExtractors(unittest.TestCase):
    def test_indian_cyber_patterns(self):
        rx = RegexExtractor()
        text = "Pay ₹4,50,000 to vikram.sharma@paytm or A/C 918273645012 IFSC HDFC0001234. Call +919876543210."
        exts = rx.extract(text)
        types = {e.entity_type for e in exts}
        self.assertIn("AMOUNT", types)
        self.assertIn("UPI", types)
        self.assertIn("ACCOUNT", types)
        self.assertIn("IFSC", types)
        self.assertIn("PHONE", types)


class TestGraphBuilder(unittest.TestCase):
    def setUp(self):
        self.entities = [
            {"canonical_value": "A", "entity_type": "PER"},
            {"canonical_value": "B", "entity_type": "PHONE"},
            {"canonical_value": "C", "entity_type": "ACCOUNT"},
            {"canonical_value": "D", "entity_type": "PER"},
        ]
        self.events = [
            {
                "event_type": "call",
                "event_timestamp": "2026-08-01T10:00:00Z",
                "entity_mentions": [
                    {"canonical_value": "A", "entity_type": "PER"},
                    {"canonical_value": "B", "entity_type": "PHONE"},
                ]
            },
            {
                "event_type": "bank_txn",
                "event_timestamp": "2026-08-01T10:15:00Z",
                "entity_mentions": [
                    {"canonical_value": "B", "entity_type": "PHONE"},
                    {"canonical_value": "C", "entity_type": "ACCOUNT"},
                ]
            }
        ]

    def test_graph_metrics(self):
        G = build_case_graph(self.entities, self.events)
        self.assertEqual(G.number_of_nodes(), 4)
        self.assertTrue(G.has_edge("A", "B"))
        self.assertTrue(G.has_edge("B", "C"))
        self.assertFalse(G.has_edge("A", "C"))

        # Node B is connected to A and C, so its degree centrality should be highest
        self.assertGreater(G.nodes["B"]["degree_centrality"], G.nodes["A"]["degree_centrality"])

        json_data = graph_to_json(G)
        self.assertEqual(len(json_data["nodes"]), 4)
        self.assertEqual(len(json_data["edges"]), 2)


class TestHiddenLinkEngine(unittest.TestCase):
    def setUp(self):
        self.G = nx.Graph()
        self.G.add_edge("A", "B")
        self.G.add_edge("B", "C")
        self.G.add_edge("A", "D")
        self.G.add_edge("D", "C")
        # A and C share neighbors B and D!
        self.G.nodes["A"]["timestamps"] = ["2026-08-01T10:00:00Z"]
        self.G.nodes["C"]["timestamps"] = ["2026-08-01T10:05:00Z"]

    def test_feature_functions(self):
        cn = common_neighbors(self.G, "A", "C")
        self.assertEqual(cn, 2)

        jac = jaccard(self.G, "A", "C")
        self.assertEqual(jac, 1.0)  # N(A)={B,D}, N(C)={B,D} -> Jaccard=1.0

        aa = adamic_adar(self.G, "A", "C")
        self.assertGreater(aa, 0.0)

        pa = preferential_attachment(self.G, "A", "C")
        self.assertEqual(pa, 4.0)

        tmp = temporal_co_occurrence(self.G, "A", "C")
        self.assertGreater(tmp, 0.0)

        fin = financial_correlation(50000.0, 50000.0, 100.0, 150.0)
        self.assertGreater(fin, 0.9)

    def test_engine_fit_and_save_load(self):
        X = np.array([
            [2.0, 0.8, 1.5, 0.9, 0.9, 0.5, 6.0],
            [2.0, 0.7, 1.2, 0.8, 0.8, 0.4, 4.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
            [0.0, 0.0, 0.0, 0.1, 0.0, 0.0, 2.0],
        ] * 4)
        y = np.array([1, 1, 0, 0] * 4)
        groups = np.array([0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3])

        engine = HiddenLinkEngine()
        engine.fit(X, y, groups)

        rep = engine.predict_pair(self.G, "A", "C")
        self.assertIn(rep.decision, ["flagged", "not_flagged"])

        with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as tmp:
            tmp_path = tmp.name

        engine.save(tmp_path)
        loaded = HiddenLinkEngine.load(tmp_path)
        self.assertEqual(loaded.threshold, engine.threshold)
        pathlib.Path(tmp_path).unlink()


class TestVisualizer(unittest.TestCase):
    def test_html_generation(self):
        graph_dict = {
            "case_id": "TEST-01",
            "nodes": [{"id": "A", "label": "A", "entity_type": "PER"}],
            "edges": [],
            "hidden_edges": [],
        }
        html = generate_interactive_html(graph_dict)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("TEST-01", html)


if __name__ == "__main__":
    unittest.main()
