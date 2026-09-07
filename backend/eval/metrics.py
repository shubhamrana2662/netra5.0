"""
CyberDrishti AI — Evaluation Metrics Engine
Implements strict entity-level, normalized, and per-class metrics.
"""
from collections import Counter, defaultdict
from typing import Any


def normalize_value(val: str, entity_type: str) -> str:
    """Normalize entity value for robust comparison."""
    if not val:
        return ""
    v = str(val).strip()
    if entity_type == "PHONE":
        clean = "".join(c for c in v if c.isdigit())
        if len(clean) == 10:
            return f"+91{clean}"
        elif len(clean) == 12 and clean.startswith("91"):
            return f"+{clean}"
        return clean
    elif entity_type == "UPI":
        return v.lower().replace(" ", "")
    elif entity_type == "AMOUNT":
        clean = v.lower().replace("₹", "").replace("rs.", "").replace("rs", "").replace("inr", "").replace(",", "").strip()
        try:
            if "lakh" in clean:
                num = float(clean.replace("lakh", "").strip())
                return str(num * 100000.0)
            elif "k" in clean:
                num = float(clean.replace("k", "").strip())
                return str(num * 1000.0)
            elif "crore" in clean:
                num = float(clean.replace("crore", "").strip())
                return str(num * 10000000.0)
            return str(float(clean))
        except Exception:
            return clean
    elif entity_type in ("ACCOUNT", "IFSC", "OTP"):
        return "".join(c for c in v if c.isalnum()).upper()
    return v.lower()


def evaluate_entity_predictions(
    ground_truth: list[dict[str, str]],
    predictions: list[dict[str, str]],
) -> dict[str, Any]:
    """
    Evaluate predicted entities against ground truth list of:
    [{'type': 'PER', 'value': '...'}, ...]
    """
    # 1. Strict Match: (type, raw_value)
    gt_strict = [(e["type"], e["value"].strip()) for e in ground_truth]
    pred_strict = [(e["type"], e["value"].strip()) for e in predictions]

    gt_counts = Counter(gt_strict)
    pred_counts = Counter(pred_strict)

    tp_strict = 0
    for item, p_cnt in pred_counts.items():
        if item in gt_counts:
            tp_strict += min(p_cnt, gt_counts[item])

    fp_strict = len(pred_strict) - tp_strict
    fn_strict = len(gt_strict) - tp_strict

    p_strict = tp_strict / len(pred_strict) if pred_strict else (1.0 if not gt_strict else 0.0)
    r_strict = tp_strict / len(gt_strict) if gt_strict else 1.0
    f1_strict = (2 * p_strict * r_strict) / (p_strict + r_strict) if (p_strict + r_strict) > 0 else 0.0

    # 2. Normalized Match: (type, normalized_value)
    gt_norm = [(e["type"], normalize_value(e["value"], e["type"])) for e in ground_truth]
    pred_norm = [(e["type"], normalize_value(e["value"], e["type"])) for e in predictions]

    gt_norm_counts = Counter(gt_norm)
    pred_norm_counts = Counter(pred_norm)

    tp_norm = 0
    for item, p_cnt in pred_norm_counts.items():
        if item in gt_norm_counts:
            tp_norm += min(p_cnt, gt_norm_counts[item])

    p_norm = tp_norm / len(pred_norm) if pred_norm else (1.0 if not gt_norm else 0.0)
    r_norm = tp_norm / len(gt_norm) if gt_norm else 1.0
    f1_norm = (2 * p_norm * r_norm) / (p_norm + r_norm) if (p_norm + r_norm) > 0 else 0.0

    # 3. Per-class metrics
    classes = sorted(set([e["type"] for e in ground_truth] + [e["type"] for e in predictions]))
    per_class = {}
    for cls in classes:
        cls_gt = [v for t, v in gt_norm if t == cls]
        cls_pred = [v for t, v in pred_norm if t == cls]

        cls_gt_c = Counter(cls_gt)
        cls_pred_c = Counter(cls_pred)

        cls_tp = sum(min(c, cls_gt_c.get(k, 0)) for k, c in cls_pred_c.items())
        cls_p = cls_tp / len(cls_pred) if cls_pred else 1.0
        cls_r = cls_tp / len(cls_gt) if cls_gt else 1.0
        cls_f1 = (2 * cls_p * cls_r) / (cls_p + cls_r) if (cls_p + cls_r) > 0 else 0.0

        per_class[cls] = {
            "support": len(cls_gt),
            "predicted": len(cls_pred),
            "precision": round(cls_p, 4),
            "recall": round(cls_r, 4),
            "f1": round(cls_f1, 4),
        }

    return {
        "strict": {
            "true_positives": tp_strict,
            "false_positives": fp_strict,
            "false_negatives": fn_strict,
            "precision": round(p_strict, 4),
            "recall": round(r_strict, 4),
            "f1": round(f1_strict, 4),
        },
        "normalized": {
            "true_positives": tp_norm,
            "false_positives": len(pred_norm) - tp_norm,
            "false_negatives": len(gt_norm) - tp_norm,
            "precision": round(p_norm, 4),
            "recall": round(r_norm, 4),
            "f1": round(f1_norm, 4),
        },
        "per_class": per_class,
    }
