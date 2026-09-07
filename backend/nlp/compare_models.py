#!/usr/bin/env python3
"""
CyberDrishti AI — Model Comparison Utility
Reads eval metrics from all 3 models and generates a comparison table.
"""

import argparse
import json
from pathlib import Path
from typing import Dict

def load_metrics(path: Path) -> Dict:
    """Load metrics JSON file."""
    if not path.exists():
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def generate_table(cdlm: Dict, hingbert: Dict, crf: Dict) -> str:
    """Generate ASCII comparison table."""
    table = []
    table.append("="*80)
    table.append("CyberDrishti AI — Model Comparison Report")
    table.append("="*80)
    table.append("")
    table.append(f"{'Model':<25} {'Precision':>12} {'Recall':>12} {'F1':>12}")
    table.append("-"*80)

    models = [
        ("CyberDrishtiLM (Custom)", cdlm),
        ("HingBERT Fine-tuned", hingbert),
        ("CRF Baseline", crf),
    ]

    for name, metrics in models:
        p = metrics.get("precision", 0.0)
        r = metrics.get("recall", 0.0)
        f1 = metrics.get("f1", 0.0)
        table.append(f"{name:<25} {p:>12.4f} {r:>12.4f} {f1:>12.4f}")

    table.append("="*80)

    # Find winner
    winner = max(models, key=lambda x: x[1].get("f1", 0.0))
    table.append(f"\n🏆 Winner: {winner[0]} (F1 = {winner[1].get('f1', 0.0):.4f})")
    table.append("")

    return "\n".join(table)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cdlm_metrics", required=True, help="CyberDrishtiLM eval_metrics.json")
    parser.add_argument("--hingbert_metrics", required=True, help="HingBERT eval_metrics.json")
    parser.add_argument("--crf_metrics", required=True, help="CRF eval_metrics.json")
    parser.add_argument("--output_report", required=True, help="Output JSON path")
    parser.add_argument("--output_table", required=True, help="Output ASCII table path")
    args = parser.parse_args()

    # Load all metrics
    cdlm = load_metrics(Path(args.cdlm_metrics))
    hingbert = load_metrics(Path(args.hingbert_metrics))
    crf = load_metrics(Path(args.crf_metrics))

    # Generate comparison
    comparison = {
        "cyberdrishtilm": cdlm,
        "hingbert": hingbert,
        "crf": crf,
    }

    # Save JSON
    with open(args.output_report, "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2)

    # Generate and save ASCII table
    table = generate_table(cdlm, hingbert, crf)
    with open(args.output_table, "w", encoding="utf-8") as f:
        f.write(table)

    print(table)
    print(f"\n📊 Reports saved:")
    print(f"   JSON: {args.output_report}")
    print(f"   Table: {args.output_table}")

if __name__ == "__main__":
    main()
