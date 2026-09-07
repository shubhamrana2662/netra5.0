"""Feature 1 tests — every threshold is config-driven; no case data baked in."""
import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from engine import FingerprintEngine, MinHash, canonical_tuple, load_config


def make_events(rows):
    """rows: (timestamp, amount, reference, type, account)"""
    return [
        {"event_type": t, "timestamp": ts, "amount": amt, "reference": ref, "account": acc}
        for ts, amt, ref, t, acc in rows
    ]


ROWS_A = make_events([
    ("2026-04-22T11:24:00", "68000.00", "UPI/719462", "bank_txn", "482913"),
    ("2026-04-22T11:27:00", "68000.00", "UPI/881201", "bank_txn", "771002"),
    ("2026-04-22T10:02:00", "12500", "IMPS/5532", "bank_txn", "482913"),
])

ROWS_A_PLUS_5 = ROWS_A + make_events([
    ("2026-04-23T09:10:00", "30000", "UPI/900112", "bank_txn", "482913"),
    ("2026-04-23T09:15:00", "30000", "UPI/900113", "bank_txn", "482913"),
    ("2026-04-23T09:22:00", "15000", "UPI/900114", "bank_txn", "771002"),
    ("2026-04-23T09:30:00", "7000", "ATM/DEL", "atm_cashout", "771002"),
    ("2026-04-23T09:31:00", "7000", "ATM/BLR", "atm_cashout", "771002"),
])

ROWS_OTHER = make_events([
    ("2026-05-01T08:00:00", "999", "UPI/111111", "bank_txn", "999999"),
    ("2026-05-01T08:05:00", "500", "UPI/222222", "bank_txn", "888888"),
])


def fake_pdf_bytes(seed: str, extra: str = "") -> bytes:
    return f"%PDF-1.7 synthetic statement payload {seed} {extra}".encode() * 40


@pytest.fixture
def engine():
    return FingerprintEngine()


# --- Tier 1: exact byte identity -------------------------------------------

def test_exact_duplicate_regardless_of_filename(engine):
    raw = fake_pdf_bytes("alpha")
    fp1 = engine.compute(raw, ROWS_A)
    fp2 = engine.compute(raw, ROWS_A)
    assert engine.compare(fp1, fp2)["verdict"] == "EXACT_DUPLICATE"
    assert engine.compare(fp1, fp2)["jaccard_estimate"] == 1.0


# --- Tier 3: content-level variant detection --------------------------------

def test_appended_rows_detected_as_variant_with_diff(engine):
    raw_old = fake_pdf_bytes("alpha")
    raw_new = fake_pdf_bytes("alpha", "reissued with new rows")
    prior = [("ev-001", engine.compute(raw_old, ROWS_A), ROWS_A)]
    result = engine.classify_upload(raw_new, ROWS_A_PLUS_5, prior)
    assert result["verdict"] == "VARIANT"
    assert result["matched_evidence_id"] == "ev-001"
    assert result["diff"]["added_rows"] == 5
    assert result["diff"]["unchanged_rows"] == 3
    assert result["diff"]["removed_rows"] == 0


def test_modified_row_shows_as_added_plus_removed(engine):
    modified = [dict(r) for r in ROWS_A]
    modified[0]["amount"] = "69000.00"  # tampered amount
    diff = engine.structural_diff(ROWS_A, modified)
    assert diff.summary["unchanged_rows"] == 2
    assert diff.summary["added_rows"] == 1
    assert diff.summary["removed_rows"] == 1


def test_completely_different_document_is_distinct(engine):
    fp_a = engine.compute(fake_pdf_bytes("alpha"), ROWS_A)
    fp_b = engine.compute(fake_pdf_bytes("omega"), ROWS_OTHER)
    result = engine.compare(fp_a, fp_b)
    assert result["verdict"] == "DISTINCT"
    assert result["jaccard_estimate"] < engine.config["jaccard_threshold"]


# --- Guardrail: near-dup must share the key field ---------------------------

def test_shared_key_guardrail_blocks_false_merge():
    eng = FingerprintEngine(require_shared_key=True, key_field="account")
    # same transaction tuples but every account value differs → must NOT merge
    rows_b = make_events([
        (r["timestamp"], r["amount"], r["reference"], r["event_type"], "DIFFERENT")
        for r in ROWS_A
    ])
    fp_a = eng.compute(fake_pdf_bytes("alpha"), ROWS_A)
    fp_b = eng.compute(fake_pdf_bytes("beta"), rows_b)  # different bytes → not EXACT
    result = eng.compare(fp_a, fp_b)
    # identical transaction rows on a DIFFERENT account = same-template forgery
    # signature: surfaced for review, never silently merged
    assert result["verdict"] == "REVIEW_SIMILAR"
    assert "no shared key" in result["reason"]
    # strict mode still hard-blocks
    eng_strict = FingerprintEngine(require_shared_key=True, key_field="account",
                                   strict_guardrail=True)
    r2 = eng_strict.compare(fp_a, fp_b)
    assert r2["verdict"] == "DISTINCT"


def test_guardrail_passes_when_key_shared():
    eng = FingerprintEngine(require_shared_key=True, key_field="account")
    fp_a = eng.compute(fake_pdf_bytes("alpha"), ROWS_A)
    fp_b = eng.compute(fake_pdf_bytes("beta"), ROWS_A_PLUS_5)
    assert eng.compare(fp_a, fp_b)["verdict"] == "VARIANT"


# --- Normalization -----------------------------------------------------------

def test_amount_normalization_is_format_insensitive():
    a = canonical_tuple({"event_type": "bank_txn", "timestamp": "2026-04-22",
                         "amount": "₹1,23,456.50", "reference": "X"},
                        ["event_type", "timestamp", "amount", "reference"])
    b = canonical_tuple({"event_type": "bank_txn", "timestamp": "2026-04-22",
                         "amount": "123456.50", "reference": "x"},
                        ["event_type", "timestamp", "amount", "reference"])
    assert a == b


# --- MinHash estimator properties --------------------------------------------

def test_minhash_estimate_accuracy_and_determinism():
    import random
    rng = random.Random(42)
    universe = [f"item-{i}" for i in range(2000)]
    set_a = set(rng.sample(universe, 500))
    # true Jaccard 0.5: 250 shared, 250 unique each
    shared = set(list(set_a)[:250])
    set_b = shared | set(rng.sample(sorted(set(universe) - set_a), 250))
    mh1 = MinHash.from_items(set_a, num_perm=128, seed=7)
    mh2 = MinHash.from_items(set_b, num_perm=128, seed=7)
    true_j = len(set_a & set_b) / len(set_a | set_b)
    est = mh1.estimated_jaccard(mh2)
    assert abs(est - true_j) <= 0.15  # within ~3.5 SE of the true value
    # determinism
    assert MinHash.from_items(set_a, num_perm=128, seed=7).signature == mh1.signature


def test_minhash_empty_sets_are_identical():
    m = MinHash.from_items([], num_perm=16, seed=0)
    assert m.estimated_jaccard(MinHash.from_items([], num_perm=16, seed=0)) == 1.0


# --- classify_upload edge cases ----------------------------------------------

def test_upload_with_no_prior_is_new(engine):
    result = engine.classify_upload(fake_pdf_bytes("zeta"), ROWS_A, [])
    assert result["verdict"] == "NEW"
    assert result["matched_evidence_id"] is None


def test_best_match_wins_when_multiple_priors(engine):
    raw_old = fake_pdf_bytes("alpha")
    prior = [
        ("ev-other", engine.compute(fake_pdf_bytes("omega"), ROWS_OTHER), ROWS_OTHER),
        ("ev-true", engine.compute(raw_old, ROWS_A), ROWS_A),
    ]
    result = engine.classify_upload(fake_pdf_bytes("alpha", "reissued"), ROWS_A_PLUS_5, prior)
    assert result["matched_evidence_id"] == "ev-true"


def test_identical_reupload_is_exact_even_against_variant_rows(engine):
    raw_old = fake_pdf_bytes("alpha")
    prior = [("ev-001", engine.compute(raw_old, ROWS_A), ROWS_A)]
    result = engine.classify_upload(raw_old, ROWS_A, prior)
    assert result["verdict"] == "EXACT_DUPLICATE"
    assert "diff" not in result  # no diff work needed for exact


# --- Config discipline --------------------------------------------------------

def test_valid_config_overrides_defaults():
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump({"jaccard_threshold": 0.9, "require_shared_key": True}, fh)
        path = fh.name
    try:
        cfg = load_config(path)
        assert cfg["jaccard_threshold"] == 0.9
        assert cfg["require_shared_key"] is True
        assert cfg["seed"] == 0  # untouched default survives
    finally:
        os.unlink(path)


def test_unknown_key_rejected_directly():
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump({"not_a_real_key": True}, fh)
        path = fh.name
    try:
        with pytest.raises(ValueError, match="unknown config keys"):
            load_config(path)
    finally:
        os.unlink(path)


# --- TLSH tier (conditional on library availability) --------------------------

def test_tlsh_tier_when_available(engine):
    if not engine.tlsh_available:
        pytest.skip("py-tlsh not installed in sandbox; production build imports it")
    fp_a = engine.compute(fake_pdf_bytes("alpha"), ROWS_A)
    fp_b = engine.compute(fake_pdf_bytes("alpha", "trailing whitespace"), ROWS_A)
    assert engine.compare(fp_a, fp_b)["tlsh_distance"] is not None


def test_tampered_copy_flags_for_review_not_silent_distinct(engine):
    """A doctored statement (one edited row) must be surfaced to the
    investigator — never silently DISTINCT, never auto-merged either."""
    tampered = [dict(r) for r in ROWS_A]
    tampered[0]["amount"] = "6000.00"
    prior = [("EV-001", engine.compute(fake_pdf_bytes("alpha"), ROWS_A), ROWS_A)]
    result = engine.classify_upload(fake_pdf_bytes("tampered"), tampered, prior)
    assert result["verdict"] == "REVIEW_SIMILAR"
    assert "edited" in result["reason"]
