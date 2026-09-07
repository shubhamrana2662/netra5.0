from __future__ import annotations
"""
CyberDrishti AI — Real Evaluation Harness (Phase 2)
Executes genuine model and heuristic inference against locked and adversarial evaluation splits.
NEVER emits placeholder constants.
"""
import json
import pathlib
import pickle
import re
import sys
import time
from typing import Any, List

BACKEND_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from correlation.regex_extractors import RegexExtractor
from eval.metrics import evaluate_entity_predictions

ARTIFACTS_DIR = BACKEND_DIR / "artifacts"
EVAL_DIR = ARTIFACTS_DIR / "evaluation"
LOCKED_TEST_PATH = EVAL_DIR / "locked_test_cases.json"
ADV_TEST_PATH = EVAL_DIR / "adversarial_test_cases.json"
CRF_MODEL_PATH = ARTIFACTS_DIR / "crf" / "crf_model.pkl"


# ── Feature extraction for CRF matching exact training features ───────────────

def crf_word_features(sent: List[str], i: int) -> dict:
    word = sent[i]
    features = {
        "bias": 1.0,
        "word.lower()": word.lower(),
        "word[-3:]": word[-3:],
        "word[-2:]": word[-2:],
        "word.isupper()": word.isupper(),
        "word.istitle()": word.istitle(),
        "word.isdigit()": word.isdigit(),
        "word.isalpha()": word.isalpha(),
        "word.isalnum()": word.isalnum(),
        "word.length": len(word),
        "has.digit": bool(re.search(r"\d", word)),
        "has.hyphen": "-" in word,
        "has.dot": "." in word,
        "has.@": "@" in word,
        "has.+91": word.startswith("+91"),
        "has.rupee": "₹" in word or word.lower() in ["rs", "inr"],
    }
    if i > 0:
        word_prev = sent[i - 1]
        features.update({
            "-1:word.lower()": word_prev.lower(),
            "-1:word.istitle()": word_prev.istitle(),
            "-1:word.isupper()": word_prev.isupper(),
            "-1:word.isdigit()": word_prev.isdigit(),
        })
    else:
        features["BOS"] = True

    if i < len(sent) - 1:
        word_next = sent[i + 1]
        features.update({
            "+1:word.lower()": word_next.lower(),
            "+1:word.istitle()": word_next.istitle(),
            "+1:word.isupper()": word_next.isupper(),
            "+1:word.isdigit()": word_next.isdigit(),
        })
    else:
        features["EOS"] = True

    return features


def extract_crf_entities(tokens: List[str], tags: List[str]) -> list[dict[str, str]]:
    """Decode IOB2 tag sequences into entity list."""
    entities = []
    curr_type = None
    curr_tokens = []

    for tok, tag in zip(tokens, tags):
        if tag.startswith("B-"):
            if curr_type and curr_tokens:
                entities.append({"type": curr_type, "value": " ".join(curr_tokens)})
            curr_type = tag[2:]
            curr_tokens = [tok]
        elif tag.startswith("I-") and curr_type == tag[2:]:
            curr_tokens.append(tok)
        else:
            if curr_type and curr_tokens:
                entities.append({"type": curr_type, "value": " ".join(curr_tokens)})
            curr_type = None
            curr_tokens = []

    if curr_type and curr_tokens:
        entities.append({"type": curr_type, "value": " ".join(curr_tokens)})

    return entities


# ── Evaluators ────────────────────────────────────────────────────────────────

def evaluate_regex(dataset: list[dict]) -> dict[str, Any]:
    rx = RegexExtractor()
    all_gt = []
    all_preds = []
    start_time = time.perf_counter()

    for item in dataset:
        text = item["text"]
        gt = item["entities"]
        all_gt.extend(gt)

        extractions = rx.extract(text)
        preds = [{"type": e.entity_type, "value": e.raw_value} for e in extractions]
        all_preds.extend(preds)

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    metrics = evaluate_entity_predictions(all_gt, all_preds)
    metrics["latency_ms_total"] = round(elapsed_ms, 2)
    metrics["latency_ms_per_doc"] = round(elapsed_ms / max(1, len(dataset)), 2)
    return metrics


def evaluate_crf(dataset: list[dict], model_path: pathlib.Path) -> dict[str, Any]:
    if not model_path.exists():
        return {"error": f"CRF model artifact not found at {model_path}"}

    with open(model_path, "rb") as f:
        crf_model = pickle.load(f)

    all_gt = []
    all_preds = []
    start_time = time.perf_counter()

    for item in dataset:
        tokens = item["tokens"]
        gt = item["entities"]
        all_gt.extend(gt)

        features = [crf_word_features(tokens, i) for i in range(len(tokens))]
        pred_tags = crf_model.predict([features])[0]
        preds = extract_crf_entities(tokens, pred_tags)
        all_preds.extend(preds)

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    metrics = evaluate_entity_predictions(all_gt, all_preds)
    metrics["latency_ms_total"] = round(elapsed_ms, 2)
    metrics["latency_ms_per_doc"] = round(elapsed_ms / max(1, len(dataset)), 2)
    return metrics


def evaluate_hybrid(dataset: list[dict], model_path: pathlib.Path) -> dict[str, Any]:
    """Hybrid: Deterministic Regex handles hard identifiers; CRF supplements ambiguous context."""
    if not model_path.exists():
        return {"error": "Model artifact missing"}

    with open(model_path, "rb") as f:
        crf_model = pickle.load(f)
    rx = RegexExtractor()

    all_gt = []
    all_preds = []
    start_time = time.perf_counter()

    for item in dataset:
        text = item["text"]
        tokens = item["tokens"]
        gt = item["entities"]
        all_gt.extend(gt)

        # 1. Regex extractions (high precision for phone, upi, ifsc, etc.)
        extractions = rx.extract(text)
        preds = [{"type": e.entity_type, "value": e.raw_value} for e in extractions]

        # 2. CRF extractions (supplements PER and KEYWORD)
        features = [crf_word_features(tokens, i) for i in range(len(tokens))]
        pred_tags = crf_model.predict([features])[0]
        crf_preds = extract_crf_entities(tokens, pred_tags)

        # Merge non-conflicting CRF entities (especially PER and KEYWORD)
        existing_vals = {p["value"].lower().strip() for p in preds}
        for cp in crf_preds:
            c_val = cp["value"].lower().strip()
            if cp["type"] in ("PER", "KEYWORD", "BANK", "LOCATION") and not any(c_val in ex or ex in c_val for ex in existing_vals):
                preds.append(cp)
                existing_vals.add(c_val)

        all_preds.extend(preds)

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    metrics = evaluate_entity_predictions(all_gt, all_preds)
    metrics["latency_ms_total"] = round(elapsed_ms, 2)
    metrics["latency_ms_per_doc"] = round(elapsed_ms / max(1, len(dataset)), 2)
    return metrics


def run_full_evaluation():
    print("================================================================")
    print("CyberDrishti AI — Real Evaluation Benchmark (Phase 2)")
    print("================================================================")

    with open(LOCKED_TEST_PATH, "r", encoding="utf-8") as f:
        locked_data = json.load(f)

    with open(ADV_TEST_PATH, "r", encoding="utf-8") as f:
        adv_data = json.load(f)

    print(f"Loaded Locked Test Set:      {len(locked_data)} documents")
    print(f"Loaded Adversarial Test Set:  {len(adv_data)} documents\n")

    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime()),
        "locked_test_set": {
            "num_documents": len(locked_data),
            "regex_extractor": evaluate_regex(locked_data),
            "crf_model": evaluate_crf(locked_data, CRF_MODEL_PATH),
            "hybrid_extractor": evaluate_hybrid(locked_data, CRF_MODEL_PATH),
        },
        "adversarial_test_set": {
            "num_documents": len(adv_data),
            "regex_extractor": evaluate_regex(adv_data),
            "crf_model": evaluate_crf(adv_data, CRF_MODEL_PATH),
            "hybrid_extractor": evaluate_hybrid(adv_data, CRF_MODEL_PATH),
        }
    }

    # Print Summary Table
    print("--- LOCKED TEST SET RESULTS (Strict / Normalized F1) ---")
    for model_name, m in report["locked_test_set"].items():
        if isinstance(m, dict) and "strict" in m:
            strict_f1 = m["strict"]["f1"]
            norm_f1 = m["normalized"]["f1"]
            lat = m["latency_ms_per_doc"]
            print(f"  {model_name:20s} | Strict F1: {strict_f1:.4f} | Norm F1: {norm_f1:.4f} | Latency: {lat:.1f}ms/doc")

    print("\n--- ADVERSARIAL TEST SET RESULTS (Strict / Normalized F1) ---")
    for model_name, m in report["adversarial_test_set"].items():
        if isinstance(m, dict) and "strict" in m:
            strict_f1 = m["strict"]["f1"]
            norm_f1 = m["normalized"]["f1"]
            lat = m["latency_ms_per_doc"]
            print(f"  {model_name:20s} | Strict F1: {strict_f1:.4f} | Norm F1: {norm_f1:.4f} | Latency: {lat:.1f}ms/doc")

    out_path = EVAL_DIR / "evaluation_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\nSaved full evaluation report to: {out_path}")
    return report


if __name__ == "__main__":
    run_full_evaluation()
