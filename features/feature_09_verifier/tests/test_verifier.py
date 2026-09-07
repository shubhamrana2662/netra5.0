"""Feature 9 tests — verifier correctness on sourced statutory DB."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from engine import OutputVerifier, load_statutory_db

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "data", "statutory_db.json")

CASE_FACTS = {
    "amounts": {"68000", "12500"},
    "phones": {"9876543210"},
    "upis": {"sanjeev.kumar@okhdfc"},
}

CANNED = [
    "The prime suspect is Ankita who transferred 68000 to sanjeev kumar account "
    "while Suresh handled the calls. Issue the freeze notice immediately."
]


@pytest.fixture
def verifier():
    db = load_statutory_db(DB_PATH)
    return OutputVerifier(db, CASE_FACTS, canned_corpus=CANNED)


def test_clean_draft_passes(verifier):
    draft = ("The evidence shows ₹68,000 was credited to sanjeev.kumar@okhdfc. "
             "An offence under Section 318(4) BNS is made out. "
             "Freeze under Section 106 BNSS; requisition records via Section 94 BNSS; "
             "certify the export under Section 63 BSA.")
    result = verifier.critique(draft)
    assert result.passed, result.to_dict()


def test_pre_transition_act_citation_flagged_with_replacement(verifier):
    draft = "The accused is liable under Section 420 IPC for cheating."
    result = verifier.critique(draft)
    assert not result.passed
    v = result.statutory_violations[0]
    assert v["reason"] == "pre_transition_act"
    assert v["act"] == "IPC"
    assert v["replacement"] == "Section 318 BNS"
    assert "Section 318 BNS" in result.correction_instructions


def test_struck_down_section_66a_flagged(verifier):
    draft = "The message was sent in violation of Section 66A of the IT Act."
    result = verifier.critique(draft)
    assert not result.passed
    v = result.statutory_violations[0]
    assert v["reason"] == "not_in_force:struck_down"
    assert "Shreya Singhal" in v["detail"]


def test_unknown_section_flagged(verifier):
    draft = "Charge the accused under Section 999 BNS."
    result = verifier.critique(draft)
    assert not result.passed
    assert result.statutory_violations[0]["reason"] == "unknown_section"


def test_bare_section_resolves_when_unambiguous(verifier):
    draft = "The certificate requirement is in Section 63."
    result = verifier.critique(draft)
    assert result.passed  # only BSA has a 63 in the DB


def test_bare_section_flagged_when_ambiguous(verifier):
    db = load_statutory_db(DB_PATH)
    # add a second act carrying section 106 to force ambiguity
    db["sections"].append({"act": "IT Act", "section": "106", "title": "test",
                           "status": "in_force", "source": "test", "replaces": None})
    verifier = OutputVerifier(db, CASE_FACTS)
    result = verifier.critique("Proceed under Section 106.")
    assert not result.passed
    assert result.statutory_violations[0]["reason"] == "ambiguous_reference"


def test_ungrounded_amount_flagged_with_search_index(verifier):
    draft = "The victim transferred ₹99,999 to the mule account."
    result = verifier.critique(draft)
    assert not result.passed
    g = result.grounding_failures[0]
    assert g["claim_type"] == "amounts"
    assert "68000.0" in g["searched_in"]  # proves the real case index was searched
    assert "remove or correct '99,999'" in result.correction_instructions


def test_indian_format_amount_normalizes(verifier):
    draft = "A sum of ₹68,000 was credited."
    assert verifier.check_grounding(draft) == []


def test_ungrounded_phone_and_upi_flagged(verifier):
    draft = ("Contact 9123456780 or pay to fraudster@paytm; "
             "the real number 9876543210 is already known.")
    failures = verifier.check_grounding(draft)
    kinds = {f["claim_type"]: f["value"] for f in failures}
    assert kinds.get("phones") == "9123456780"
    assert kinds.get("upis") == "fraudster@paytm"
    assert "9876543210" not in kinds.values()  # known value not flagged


def test_canned_text_detection(verifier):
    draft = ("The prime suspect is Ankita who transferred 68000 to sanjeev kumar "
             "account while Suresh handled the calls. Issue the freeze notice immediately.")
    result = verifier.critique(draft)
    assert not result.passed
    assert result.canned_detections[0]["similarity"] >= 0.60
    assert "only from the retrieved evidence" in result.correction_instructions


def test_passed_verifier_result_serializable(verifier):
    draft = "₹12,500 was debited; see Section 66C IT Act."
    result = verifier.critique(draft)
    d = result.to_dict()
    assert d["passed"] is True and d["statutory_violations"] == []
