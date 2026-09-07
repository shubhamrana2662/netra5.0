from __future__ import annotations
"""
CyberDrishti AI — Model Comparison Utility
Reads evaluation metrics from all models and generates model_comparison.json & model_comparison_table.txt.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


def load_metrics(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "status": "NOT EVALUATED"}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        if "eval_ner_f1_macro" in data:
            data["f1"] = data["eval_ner_f1_macro"]
        elif "ner_f1" in data:
            data["f1"] = data["ner_f1"]
        return data


def generate_comparison(artifacts_dir: Path) -> str:
    crf_metrics = load_metrics(artifacts_dir / "crf" / "eval_metrics.json")
    hingbert_metrics = load_metrics(artifacts_dir / "hingbert" / "test_metrics.json")
    cdlm_metrics = load_metrics(artifacts_dir / "cyberdrishtilm" / "test_metrics.json")

    models = [
        ("CRF Baseline", crf_metrics),
        ("HingBERT Fine-tuned", hingbert_metrics),
        ("CyberDrishtiLM Transformer", cdlm_metrics),
    ]

    lines = []
    lines.append("=" * 80)
    lines.append("CyberDrishti AI — Model Comparison Report")
    lines.append("=" * 80)
    lines.append(f"{'Model':<30} {'Precision':>12} {'Recall':>12} {'F1-Score':>12}")
    lines.append("-" * 80)

    for name, m in models:
        p = m.get("precision", 0.0)
        r = m.get("recall", 0.0)
        f1 = m.get("f1", 0.0)
        lines.append(f"{name:<30} {p:>12.4f} {r:>12.4f} {f1:>12.4f}")

    lines.append("=" * 80)
    winner = max(models, key=lambda x: x[1].get("f1", 0.0))
    lines.append(f"\n🏆 Primary Contextual NER Model: {winner[0]} (F1 = {winner[1].get('f1', 0.0):.4f})\n")

    report_text = "\n".join(lines)

    # Save JSON & ASCII table
    comparison_json = {
        "crf": crf_metrics,
        "hingbert": hingbert_metrics,
        "cyberdrishtilm": cdlm_metrics,
        "primary_model": winner[0],
    }

    with open(artifacts_dir / "model_comparison.json", "w") as f:
        json.dump(comparison_json, f, indent=2)

    with open(artifacts_dir / "model_comparison_table.txt", "w") as f:
        f.write(report_text)

    return report_text


def main():
    base_dir = Path(__file__).resolve().parent.parent.parent
    artifacts_dir = base_dir / "artifacts"
    report = generate_comparison(artifacts_dir)
    print(report)


if __name__ == "__main__":
    main()
