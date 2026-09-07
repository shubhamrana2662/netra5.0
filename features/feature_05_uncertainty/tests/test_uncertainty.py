"""Feature 5 tests — quantile math, coverage, abstention, honesty flags."""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from engine import calibrate, empirical_coverage, predict_set


def test_exact_quantile_small_sample():
    scores = [0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.00]  # n=10
    cal = calibrate(scores, epsilon=0.05, source="real_x", model_name="m")
    # ceil((10+1)*0.95) = ceil(10.45) = 11 → beyond sample → inf
    assert cal["quantile_threshold"] == float("inf")
    cal2 = calibrate(scores, epsilon=0.15, source="real_x", model_name="m")
    # ceil(11*0.85) = ceil(9.35) = 10 → 10th smallest = 1.00
    assert cal2["quantile_threshold"] == 1.00
    cal3 = calibrate(scores, epsilon=0.25, source="real_x", model_name="m")
    # ceil(11*0.75) = ceil(8.25) = 9 → 9th smallest = 0.90
    assert cal3["quantile_threshold"] == 0.90


def test_invalid_inputs_rejected():
    with pytest.raises(ValueError):
        calibrate([0.1], epsilon=0.0)
    with pytest.raises(ValueError):
        calibrate([], epsilon=0.05)


def test_empirical_coverage_holds_guarantee_on_exchangeable_data():
    """Simulate a well-specified scorer: true label gets low α with prob 0.97.
    With calibration from the same distribution, coverage must hold ≥ 1−ε."""
    rng = random.Random(7)
    def draw():
        true_alpha = 0.05 if rng.random() < 0.97 else rng.uniform(0.5, 1.0)
        return true_alpha, {f"L{i}": rng.random() for i in range(4)} | {"true": true_alpha}
    cal_scores = [draw()[0] for _ in range(500)]
    cal = calibrate(cal_scores, epsilon=0.10, source="real_sim")
    hits = []
    for _ in range(1000):
        true_alpha, cands = draw()
        cands["true"] = true_alpha
        ps = predict_set(cal, cands)
        hits.append("true" in ps["prediction_set"])
    cov = empirical_coverage(cal, hits)
    assert cov >= 0.90, cov  # the 1−ε guarantee, checked empirically


def test_synthetic_calibration_marks_guarantee_invalid():
    cal = calibrate([0.1, 0.2, 0.3], epsilon=0.05, source="synthetic_v2")
    assert cal["coverage_guarantee"]["valid_for_real_data"] is False
    assert "exchangeable" in cal["coverage_guarantee"]["statement"]


def test_single_label_prediction_set():
    cal = calibrate([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0] * 3,
                    epsilon=0.25, source="real_x")
    out = predict_set(cal, {"mule": 0.05, "victim": 0.85, "kingpin": 0.95})
    assert out["verdict"] == "SINGLE_LABEL"
    assert out["prediction_set"] == ["mule"]


def test_ambiguous_set_tells_the_officer_the_truth():
    cal = calibrate([0.05] * 20, epsilon=0.05, source="real_x")  # q̂ = 0.05
    out = predict_set(cal, {"mule": 0.05, "victim": 0.05})
    assert out["verdict"] == "AMBIGUOUS_SET"
    assert "cannot distinguish" in out["message"]


def test_empty_set_is_explicit_abstention():
    # n must exceed 1/ε for a finite q̂ to exist (conformal rank ⌈(n+1)(1−ε)⌉)
    cal = calibrate([0.01] * 20, epsilon=0.05, source="real_x")
    out = predict_set(cal, {"mule": 0.9, "victim": 0.95})
    assert out["verdict"] == "OUT_OF_DISTRIBUTION"
    assert out["prediction_set"] == []
    assert "Abstain" in out["message"]
