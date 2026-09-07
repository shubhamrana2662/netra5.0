"""Feature 6 tests — ranking honesty, drafts, blocking, disclosure."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from engine import load_catalog, rank_actions

CATALOG = load_catalog(os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "data", "action_catalog.json"))

CASE_STATE = {
    "elapsed_hours_since_first_credit": 1.0,
    "complaint_ref": "NCRP-2026-001234",
    "accounts_at_risk": [
        {"account": "4829101112", "ifsc": "SHCB0000123", "bank_name": "Sahyadri Commercial Bank",
         "amount_unwithdrawn": 450000},
        {"account": "7710023344", "ifsc": "MRDN0000456", "bank_name": "Meridian Bank of India",
         "amount_unwithdrawn": 80000},
    ],
    "unresolved_phones": [
        {"phone": "9812345670", "period_start": "2026-04-20", "period_end": "2026-04-23"}
    ],
    "crime_window_cells": [
        {"cell_id": "IPT-TWR-021", "period_start": "2026-04-22T11:00", "period_end": "2026-04-22T12:00"}
    ],
}


def test_freeze_of_largest_amount_ranks_first():
    out = rank_actions(CASE_STATE, CATALOG)
    top = out["ranked_actions"][0]
    assert top["action_code"] == "FREEZE_ACCOUNT_EVIDENCE"
    assert top["target"]["account"] == "4829101112"
    assert top["status"] == "ready"


def test_1930_referral_is_present_and_cheap():
    out = rank_actions(CASE_STATE, CATALOG)
    referral = next(a for a in out["ranked_actions"]
                    if a["action_code"] == "HELPLINE_1930_REFERRAL")
    assert referral["status"] == "ready"
    assert referral["components"]["friction_penalty"] <= 0.1


def test_weights_disclosed_in_every_result():
    out = rank_actions(CASE_STATE, CATALOG)
    assert all("weights_used" in a for a in out["ranked_actions"])
    assert all("utility_score" in a for a in out["ranked_actions"] if a["status"] == "ready")


def test_draft_filled_only_from_case_data_and_banner_present():
    out = rank_actions(CASE_STATE, CATALOG)
    freeze = next(a for a in out["ranked_actions"]
                  if a["action_code"] == "FREEZE_ACCOUNT_EVIDENCE"
                  and a["target"]["account"] == "4829101112")
    assert "4829101112" in freeze["draft"]
    assert "450000" in freeze["draft"]
    assert "Section 106 BNSS" in freeze["statutory_basis"]
    assert freeze["banner"].startswith("DRAFT")


def test_missing_fields_block_draft_without_fabrication():
    state = {
        "elapsed_hours_since_first_credit": 0.5,
        "complaint_ref": "NCRP-1",
        "accounts_at_risk": [{"account": "123", "amount_unwithdrawn": 1000}],  # no ifsc/bank
        "unresolved_phones": [],
        "crime_window_cells": [],
    }
    out = rank_actions(state, CATALOG)
    blocked = [a for a in out["ranked_actions"] if a["status"] == "blocked_missing_fields"]
    assert blocked, "expected blocked actions"
    freeze_block = next(a for a in blocked if a["action_code"] == "FREEZE_ACCOUNT_EVIDENCE")
    assert set(freeze_block["missing_fields"]) == {"ifsc", "bank_name"}
    assert freeze_block["draft"] is None
    assert freeze_block["utility_score"] is None


def test_urgency_decays_with_elapsed_time():
    fresh = rank_actions({**CASE_STATE, "elapsed_hours_since_first_credit": 0.1}, CATALOG)
    stale = rank_actions({**CASE_STATE, "elapsed_hours_since_first_credit": 12.0}, CATALOG)
    f = next(a for a in fresh["ranked_actions"] if a["action_code"] == "FREEZE_ACCOUNT_EVIDENCE")
    s = next(a for a in stale["ranked_actions"] if a["action_code"] == "FREEZE_ACCOUNT_EVIDENCE")
    assert f["urgency_factor"] > s["urgency_factor"]
    assert f["utility_score"] > s["utility_score"]


def test_weight_changes_flip_ranking_and_are_disclosed():
    heavy_friction = {"friction": 50.0}
    out = rank_actions(CASE_STATE, CATALOG, weights=heavy_friction)
    top = out["ranked_actions"][0]
    # with friction dominating, the cheapest action (1930 referral) rises
    assert top["action_code"] == "HELPLINE_1930_REFERRAL"
    assert top["weights_used"]["friction"] == 50.0


def test_catalog_validation_rejects_incomplete_action():
    bad = {"golden_hours": 2, "actions": [{"code": "X"}]}
    import json, tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(bad, fh)
        path = fh.name
    try:
        with pytest.raises(ValueError, match="missing 'statute'"):
            load_catalog(path)
    finally:
        os.unlink(path)


def test_note_is_honest_about_heuristic():
    out = rank_actions(CASE_STATE, CATALOG)
    assert "not a calibrated Value-of-Information estimate" in out["note"]
