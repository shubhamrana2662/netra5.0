"""CyberDrishti Feature 5 — Split-Conformal Uncertainty (isolated build).

Replaces naked softmax confidence ("99% sure — mule") with prediction SETS
that carry a distribution-free marginal coverage guarantee:
P(Y ∈ C(X)) ≥ 1 − ε, valid under exchangeability of calibration and deploy-
ment data. If the calibration set is synthetic (ours initially is), the
engine says so and marks the guarantee INVALID for real-data claims — no
quiet laundering of synthetic coverage into a real-world promise.

Mechanics (split/inductive conformal, Vovk et al. 2005; Angelopoulos & Bates
arXiv:2107.07511): calibration non-conformity scores α_i = 1 − p̂(y_i|x_i);
threshold q̂ = the ⌈(n+1)(1−ε)⌉-th smallest score (clipped; beyond the sample
→ ∞, meaning an empty set is possible and reported as abstention);
C(x) = {y : α(x,y) ≤ q̂}.

Empty set → explicit OUT_OF_DISTRIBUTION abstention. |C(x)| > 1 → "the data
cannot distinguish these; more evidence required" — exactly the honest
sentence an officer needs.
"""
from __future__ import annotations

import math
from typing import Any


def calibrate(
    scores: list[float],
    epsilon: float = 0.05,
    source: str = "unspecified",
    model_name: str = "unknown",
) -> dict[str, Any]:
    if not 0 < epsilon < 1:
        raise ValueError("epsilon must be in (0, 1)")
    if not scores:
        raise ValueError("calibration scores required")
    s = sorted(scores)
    n = len(s)
    rank = math.ceil((n + 1) * (1 - epsilon))  # 1-indexed order statistic
    q = s[rank - 1] if rank <= n else math.inf
    return {
        "model_name": model_name,
        "epsilon": epsilon,
        "n": n,
        "quantile_threshold": q,
        "source": source,
        "coverage_guarantee": {
            "statement": f"P(Y ∈ C(X)) >= {1 - epsilon:.2f} (marginal, exchangeable data)",
            "valid_for_real_data": source.startswith("real"),
        },
    }


def predict_set(
    calibration: dict[str, Any],
    candidate_scores: dict[str, float],
) -> dict[str, Any]:
    """candidate_scores: {label: non-conformity α(x,y)}. α ≤ q̂ → in the set."""
    q = calibration["quantile_threshold"]
    in_set = sorted(l for l, a in candidate_scores.items() if a <= q)
    if not in_set:
        return {
            "prediction_set": [],
            "verdict": "OUT_OF_DISTRIBUTION",
            "message": ("No label satisfies the coverage threshold — the input "
                        "does not resemble the calibration distribution. "
                        "Abstain and gather more evidence."),
        }
    if len(in_set) == 1:
        message = "Single-label prediction set at the required coverage."
    else:
        message = ("At the required coverage, the data cannot distinguish "
                   "between: " + ", ".join(in_set) + ". More evidence required.")
    return {
        "prediction_set": in_set,
        "verdict": "SINGLE_LABEL" if len(in_set) == 1 else "AMBIGUOUS_SET",
        "message": message,
    }


def empirical_coverage(
    calibration: dict[str, Any],
    trial_true_label_in_set: list[bool],
) -> float:
    """Diagnostics: empirical coverage over trials (never a substitute for the
    theoretical guarantee)."""
    if not trial_true_label_in_set:
        raise ValueError("trials required")
    return sum(1 for t in trial_true_label_in_set if t) / len(trial_true_label_in_set)
