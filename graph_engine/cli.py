#!/usr/bin/env python3
"""
CyberDrishti AI — Graph Engine Command-Line Interface (CLI)
============================================================
Commands:
  demo        — Run the full end-to-end investigation graph demo
  train       — Train the 6-feature hidden link model on synthetic cases
  build       — Build graph from a case JSON file and export JSON / HTML visualizer
  inspect     — Inspect entity or pair metrics

Usage:
  python cli.py demo
  python cli.py train --cases 40 --output models/hidden_link_model.pkl
  python cli.py build --input sample_data/case_mule_syndicate.json --output-html out.html
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from core.builder import build_case_graph
from core.hidden_link_engine import HiddenLinkEngine
from core.serializer import serialize_graph_for_visualization
from visualizer import export_graph_to_html
from demo import run_demo
from trainer import train_model


def main():
    parser = argparse.ArgumentParser(
        prog="graph-engine",
        description="CyberDrishti AI — Standalone Graph Engine CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: demo
    subparsers.add_parser("demo", help="Run the full pipeline demonstration")

    # Command: train
    train_parser = subparsers.add_parser("train", help="Train hidden link prediction model")
    train_parser.add_argument("--cases", type=int, default=40, help="Number of synthetic cases")
    train_parser.add_argument("--output", type=str, default="models/hidden_link_model.pkl", help="Model output path")

    # Command: build
    build_parser = subparsers.add_parser("build", help="Build graph from case JSON file")
    build_parser.add_argument("--input", "-i", type=str, required=True, help="Path to input case JSON")
    build_parser.add_argument("--output-json", type=str, default=None, help="Path to save serialized graph JSON")
    build_parser.add_argument("--output-html", type=str, default=None, help="Path to save interactive HTML visualizer")
    build_parser.add_argument("--model", type=str, default="models/hidden_link_model.pkl", help="Path to hidden link model")

    args = parser.parse_args()

    if args.command == "demo" or len(sys.argv) == 1:
        run_demo()
    elif args.command == "train":
        train_model(output_path=args.output, num_cases=args.cases)
    elif args.command == "build":
        in_path = Path(args.input)
        if not in_path.exists():
            print(f"❌ Error: Input file not found: {in_path}")
            sys.exit(1)

        with open(in_path, "r", encoding="utf-8") as f:
            case_data = json.load(f)

        print(f"Building graph for: {case_data.get('case_id', 'Case')}")
        G = build_case_graph(case_data.get("entities", []), case_data.get("events", []))
        print(f"Graph nodes: {G.number_of_nodes()}, edges: {G.number_of_edges()}")

        hidden_links = []
        model_path = Path(args.model)
        if model_path.exists():
            engine = HiddenLinkEngine.load(model_path)
            hidden_links = engine.predict_case(G)
            print(f"Flagged {len(hidden_links)} hidden link(s) (Threshold: {engine.threshold:.4f})")
        else:
            print("Notice: No model file found, skipping hidden link prediction. (Run 'cli.py train' to train model)")

        serialized = serialize_graph_for_visualization(G, hidden_links, case_id=case_data.get("case_id"))

        if args.output_json:
            out_json = Path(args.output_json)
            out_json.parent.mkdir(parents=True, exist_ok=True)
            out_json.write_text(json.dumps(serialized, indent=2), encoding="utf-8")
            print(f"✅ Saved graph JSON to: {out_json.resolve()}")

        if args.output_html:
            out_html = Path(args.output_html)
            export_graph_to_html(serialized, out_html, title=case_data.get("title", "Case Graph"))
            print(f"✅ Saved HTML visualizer to: {out_html.resolve()}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
