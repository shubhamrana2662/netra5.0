#!/usr/bin/env python3
"""
CyberDrishti AI — Graph Engine End-to-End Demo
===============================================
Demonstrates the full 7-step graph intelligence pipeline:
1. Ingest raw investigation case events
2. Deterministic entity extraction & normalization
3. Union-Find canonicalization & resolution
4. NetworkX graph construction & co-occurrence weighting
5. Louvain community detection & boundary bridge scoring
6. Precision-gated ML hidden-link inference
7. Generation of court-admissible explainability reports & interactive HTML visualizer

Usage:
    python demo.py
"""

from __future__ import annotations

import json
from pathlib import Path

from core.canonicalizer import canonicalise_entities
from core.builder import build_case_graph
from core.extractors import RegexExtractor
from core.hidden_link_engine import HiddenLinkEngine
from core.serializer import serialize_graph_for_visualization
from visualizer import export_graph_to_html


def run_demo():
    print("=" * 70)
    print("🔍 CYBERDRISHTI AI — GRAPH ENGINE DEMONSTRATION")
    print("=" * 70)

    # 1. Load sample case
    case_path = Path(__file__).parent / "sample_data" / "case_mule_syndicate.json"
    with open(case_path, "r", encoding="utf-8") as f:
        case_data = json.load(f)

    print(f"\n[STEP 1] Loaded Case: {case_data['case_id']} — \"{case_data['title']}\"")
    print(f"Description: {case_data['description']}")
    print(f"Input Events: {len(case_data['events'])} evidence records (WhatsApp, IMPS, CDR, Netbanking)")

    # 2. Extract & resolve entities across all events
    print("\n[STEP 2] Deterministic Extraction & Entity Canonicalization...")
    rx = RegexExtractor()
    all_raw_mentions = []

    for ev in case_data["events"]:
        extractions = rx.extract(ev["text_content"])
        for ext in extractions:
            all_raw_mentions.append({
                "raw_value": ext.raw_value,
                "norm_value": ext.norm_value,
                "entity_type": ext.entity_type,
                "event_id": ev["id"],
            })

    canonical_map = canonicalise_entities(all_raw_mentions)
    print(f"Extracted {len(all_raw_mentions)} raw mentions -> Resolved into {len(canonical_map)} canonical entities:")
    for canon, mentions in canonical_map.items():
        etype = mentions[0]["entity_type"]
        print(f"  • [{etype:<7}] {canon} ({len(mentions)} mention{'s' if len(mentions) > 1 else ''})")

    # 3. Build Case Graph
    print("\n[STEP 3] Constructing NetworkX Graph & Co-occurrence Topology...")
    G = build_case_graph(case_data["entities"], case_data["events"])
    print(f"NetworkX Graph constructed:")
    print(f"  Nodes (Entities): {G.number_of_nodes()}")
    print(f"  Edges (Observed Co-occurrences): {G.number_of_edges()}")

    # 4. Topological Metrics & Communities
    print("\n[STEP 4] Louvain Community Detection & Centrality Metrics:")
    for n in G.nodes():
        deg = G.nodes[n].get("degree_centrality", 0.0)
        comm = G.nodes[n].get("community_id", 0)
        bridge = G.nodes[n].get("bridge_score", 0.0)
        print(f"  • {n:<30} | Centrality: {deg:.3f} | Comm: #{comm} | BridgeScore: {bridge:.2f}")

    # 5. Predict Hidden Links using Pretrained Model
    print("\n[STEP 5] Predicting Hidden Links (Precision-Gated >= 90%)...")
    model_path = Path(__file__).parent / "models" / "hidden_link_model.pkl"

    if model_path.exists():
        engine = HiddenLinkEngine.load(model_path)
        print(f"Loaded trained HiddenLinkEngine (Threshold: {engine.threshold:.4f})")
    else:
        print("Training fresh model...")
        from trainer import train_model
        engine = train_model(output_path=str(model_path), num_cases=25)

    hidden_links = engine.predict_case(G)
    print(f"\nFlagged {len(hidden_links)} Hidden Link(s) above precision threshold:")
    for r in hidden_links:
        print(f"\n  🚨 INFERRED LINK: {r.entities[0]} <---> {r.entities[1]}")
        print(f"     Inference Confidence Score: {r.final_score * 100:.1f}% (Threshold: {r.threshold * 100:.1f}%)")
        print(f"     Section 65B Metric Breakdown:")
        for k, v in r.component_scores.items():
            print(f"       - {k:<25}: {v:.4f}")

    # 6. Serialize Graph & Export
    print("\n[STEP 6] Serializing to Standard Graph JSON...")
    serialized = serialize_graph_for_visualization(G, hidden_links, case_id=case_data["case_id"])
    json_out = Path(__file__).parent / "sample_data" / "sample_graph.json"
    json_out.write_text(json.dumps(serialized, indent=2), encoding="utf-8")
    print(f"Saved: {json_out.resolve()}")

    # 7. Generate Standalone Interactive HTML Visualizer
    print("\n[STEP 7] Generating Standalone Interactive HTML Graph Visualizer...")
    html_out = Path(__file__).parent / "sample_data" / "sample_graph_visualization.html"
    export_graph_to_html(serialized, html_out, title=f"CyberDrishti AI - {case_data['title']}")
    print(f"Saved: {html_out.resolve()}")

    print("\n" + "=" * 70)
    print("✅ DEMO COMPLETE! Open the HTML visualizer in any web browser:")
    print(f"   file://{html_out.resolve()}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    run_demo()
