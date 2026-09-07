"""Feature 3 tests — blind index honesty, canonicalization, collision alerts."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from engine import BlindIndex, MissingKeyError, build_index, canonicalize, find_collisions


KEY = "test-department-key-do-not-use-in-prod"


def entries():
    return [
        # same UPI in 3 cases (formatting variants included)
        {"case_id": "C1", "entity_type": "UPI", "value": "Mule.Pay@OkHDFC", "degree": 3, "severity": 2.0},
        {"case_id": "C2", "entity_type": "UPI", "value": "mule.pay@okhdfc", "degree": 1, "severity": 1.0},
        {"case_id": "C3", "entity_type": "UPI", "value": "mule.pay@okhdfc ", "degree": 2, "severity": 1.0},
        # same phone in 2 cases
        {"case_id": "C1", "entity_type": "PHONE", "value": "+91 98765 43210", "degree": 2},
        {"case_id": "C4", "entity_type": "PHONE", "value": "9876543210", "degree": 1},
        # single-case identifiers → no alert
        {"case_id": "C1", "entity_type": "ACCOUNT", "value": "482910111222", "degree": 5},
        {"case_id": "C2", "entity_type": "ACCOUNT", "value": "999888777666", "degree": 1},
    ]


def test_missing_key_is_an_error_never_a_default():
    with pytest.raises(MissingKeyError):
        BlindIndex("")
    with pytest.raises(MissingKeyError):
        BlindIndex(None)


def test_canonicalization_makes_variants_collide():
    assert canonicalize("PHONE", "+91 98765 43210") == canonicalize("PHONE", "9876543210")
    assert canonicalize("UPI", "Mule.Pay@OkHDFC") == canonicalize("UPI", "mule.pay@okhdfc")
    assert canonicalize("ACCOUNT", "4829-1011-1222") == "482910111222"
    assert canonicalize("IFSC", "shcb0000123") == "SHCB0000123"


def test_unsupported_entity_type_rejected():
    with pytest.raises(ValueError):
        canonicalize("Aadhaar", "1234")


def test_same_value_same_key_same_token():
    idx = BlindIndex(KEY)
    assert idx.token("UPI", "a@b") == idx.token("UPI", "A@B")
    assert idx.token("PHONE", "9876500000") == idx.token("PHONE", "+91 98765 00000")


def test_different_keys_produce_different_tokens():
    t1 = BlindIndex("key-one").token("PHONE", "9876500000")
    t2 = BlindIndex("key-two").token("PHONE", "9876500000")
    assert t1 != t2


def test_collision_alert_carries_no_raw_identifier():
    store = build_index(entries(), BlindIndex(KEY))
    alerts = find_collisions(store)
    assert len(alerts) == 2  # UPI (3 cases) + PHONE (2 cases)
    blob = repr(alerts)
    assert "mule.pay" not in blob.lower()
    assert "9876543210" not in blob
    assert "482910111222" not in blob
    upi_alert = next(a for a in alerts if a["entity_type"] == "UPI")
    assert upi_alert["case_ids"] == ["C1", "C2", "C3"]
    assert upi_alert["case_count"] == 3


def test_syndicate_score_prefers_high_degree_and_severity():
    store = build_index(entries(), BlindIndex(KEY))
    alerts = find_collisions(store)
    upi = next(a for a in alerts if a["entity_type"] == "UPI")
    phone = next(a for a in alerts if a["entity_type"] == "PHONE")
    # UPI: severity 2*log(4) + 1*log(2) + 1*log(3) ≈ 4.27
    # PHONE: 2*log(3) + 1*log(2) ≈ 2.90
    assert upi["syndicate_score"] > phone["syndicate_score"]


def test_single_case_identifier_never_alerts():
    store = build_index(entries(), BlindIndex(KEY))
    alerts = find_collisions(store)
    # account values appear in one case each
    assert all(a["entity_type"] != "ACCOUNT" for a in alerts)


def test_duplicate_token_case_pairs_collapse():
    entries_dup = [
        {"case_id": "C1", "entity_type": "UPI", "value": "x@y", "degree": 2},
        {"case_id": "C1", "entity_type": "UPI", "value": "x@y", "degree": 5},
        {"case_id": "C2", "entity_type": "UPI", "value": "x@y", "degree": 1},
    ]
    store = build_index(entries_dup, BlindIndex(KEY))
    tok = BlindIndex(KEY).token("UPI", "x@y")
    assert len(store[tok]) == 2  # C1 collapsed, keeping max degree
    assert next(o for o in store[tok] if o["case_id"] == "C1")["degree"] == 5
