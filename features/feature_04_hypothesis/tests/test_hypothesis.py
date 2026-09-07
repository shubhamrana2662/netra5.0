"""Feature 4 tests — mule signature ranks top, victim refuted, no fake %."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from engine import evaluate, load_model

MODEL = load_model(os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "data", "hypotheses.json"))

MULE_OBS = {
    "velocity_minutes": 8,      # fast pass-through
    "account_age_days": 5,      # fresh account
    "inbound_victim_calls": 0,  # no victims call a mule
    "dormancy_before_crime_days": 90,
}

OPERATOR_OBS = {
    "velocity_minutes": 600,    # funds leave through others, slowly
    "account_age_days": 900,
    "inbound_victim_calls": 14, # many victims call the operator
    "dormancy_before_crime_days": 10,
}


def test_classic_mule_signature_ranks_mule_first():
    out = evaluate(MULE_OBS, MODEL)
    assert out["ranked_labels"][0] == "LAYER1_MULE"
    assert out["assessment_type"] == "RULE_BASED_ASSESSMENT"
    assert out["display_label"] is not None  # honest banner present


def test_operator_signature_ranks_kingpin_first():
    out = evaluate(OPERATOR_OBS, MODEL)
    assert out["ranked_labels"][0] == "KINGPIN_ORGANIZER"


def test_mule_case_refuting_evidence_targets_victim_hypothesis():
    out = evaluate(MULE_OBS, MODEL)
    by_label = {h["label"]: h for h in out["hypotheses"]}
    refute = by_label["COMPROMISED_VICTIM"]["refuting_evidence"]
    assert refute is not None
    assert refute["likelihood_under_this_hypothesis"] <= 0.10


def test_no_percentages_without_explicit_calibration():
    out = evaluate(MULE_OBS, MODEL)
    assert all(h["posterior"] is None for h in out["hypotheses"])


def test_percentages_only_with_calibration_and_opt_in():
    out = evaluate(MULE_OBS, MODEL, config={
        "allow_percentages": True,
        "calibration": {"source": "real_labeled_cases_v1", "ece": 0.04},
    })
    posteriors = {h["label"]: h["posterior"] for h in out["hypotheses"]}
    assert all(v is not None for v in posteriors.values())
    assert abs(sum(posteriors.values()) - 1.0) < 1e-3
    assert out["assessment_type"] == "CALIBRATED_POSTERIOR"
    assert out["display_label"] is None


def test_percentages_blocked_even_if_opt_in_without_calibration():
    out = evaluate(MULE_OBS, MODEL, config={"allow_percentages": True})
    assert all(h["posterior"] is None for h in out["hypotheses"])
    assert out["assessment_type"] == "RULE_BASED_ASSESSMENT"


def test_missing_observations_reported_not_imputed():
    out = evaluate({"velocity_minutes": 8}, MODEL)
    assert "pass_through_speed" in [e["indicator"] for e in out["evidence_matrix"]]
    assert set(out["unobserved_indicators"]) >= {"account_age", "victim_contact", "dormancy"}


def test_evidence_matrix_carries_observed_values_and_diagnosticity():
    out = evaluate(MULE_OBS, MODEL)
    for e in out["evidence_matrix"]:
        assert "observed_value" in e and "bucket" in e and "diagnosticity" in e
        assert abs(sum(e["likelihoods"].values()) - 1.0) < 1e-6


def test_model_validation_rejects_bad_distributions():
    import json, tempfile
    bad = json.loads(json.dumps(MODEL))
    bad["indicators"][0]["evidence"]["fast"]["LAYER1_MULE"] = 0.99  # sums > 1
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(bad, fh)
        path = fh.name
    try:
        with pytest.raises(ValueError, match="sum to 1"):
            load_model(path)
    finally:
        os.unlink(path)
