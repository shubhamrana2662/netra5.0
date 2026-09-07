"""Feature 7 tests — trace building, matching honesty, detector citations."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from engine import classify_case, load_playbooks, normalized_levenshtein

PLAYBOOKS = load_playbooks(os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "data", "playbooks.json"))


def msgs(lines):
    return [{"line_no": i + 1, "sender": "S" if i % 2 else "V", "text": t}
            for i, t in enumerate(lines)]


DIGITAL_ARREST_CHAT = msgs([
    "sir aapke naam CBI ka arrest warrant notice aya hai parcel case mein",   # SPOOF_LE_NOTICE
    "video call par abhi aao, camera on rakho",                                # ISOLATION_VIDEO_CALL
    "verify nahi kiya to andar jana padega, non-bailable hai",                 # THREAT_ARREST
    "compliance ke liye 68000 account mein daalo aur OTP bolo",               # EXTRACTION_TRANSFER
    "kaam ho gaya, chat delete karke number block kar do",                     # DISPOSAL_BLOCK
])

INVESTMENT_CHAT = msgs([
    "sir aaj ka task complete karo, daily profit pakka milega",                # LURE_SMALL_PROFIT
    "VIP level 3 kholo, prepaid task bada milega",                              # VIP_UPSELL
    "50 hazaar deposit karo abhi",                                              # EXTRACTION_LARGE_DEPOSIT
    "withdrawal pending hai, 30% tax bhejo pehle",                              # WITHDRAWAL_BLOCK
    "aapka account closed hai, agent offline chala gaya",                       # DISPOSAL_GHOST
])

NEUTRAL_CHAT = msgs([
    "bhai shaadi ki shopping kab karenge",
    "cricket match dekhein aaj shaam ko",
    "mummy ne phone kiya, ghar aa jaldi",
])


def test_digital_arrest_chat_matches_digital_arrest_playbook():
    result = classify_case(DIGITAL_ARREST_CHAT, PLAYBOOKS)
    assert result["verdict"] == "MATCHED"
    assert result["best_match"]["playbook"] == "DIGITAL_ARREST_EXTORTION"
    assert result["best_match"]["similarity"] >= 0.60
    assert result["best_match"]["epistemic_status"] == "PREDICTED"


def test_investment_chat_matches_investment_playbook():
    result = classify_case(INVESTMENT_CHAT, PLAYBOOKS)
    assert result["verdict"] == "MATCHED"
    assert result["best_match"]["playbook"] == "INVESTMENT_TASK_FRAUD"


def test_neutral_chat_yields_no_confident_match():
    result = classify_case(NEUTRAL_CHAT, PLAYBOOKS)
    assert result["verdict"] in ("NO_CONFIDENT_MATCH", "INSUFFICIENT_TRACE")
    assert result["best_match"] is None


def test_every_matched_stage_cites_message_lines():
    result = classify_case(DIGITAL_ARREST_CHAT, PLAYBOOKS)
    for ev in result["trace_evidence"]:
        assert "line_no" in ev and ev["line_no"] >= 1
        assert "matched_text" in ev and ev["matched_text"]
    stages = [e["stage"] for e in result["trace_evidence"]]
    assert "THREAT_ARREST" in stages and "EXTRACTION_TRANSFER" in stages


def test_similarity_is_not_a_probability_claim():
    result = classify_case(DIGITAL_ARREST_CHAT, PLAYBOOKS)
    assert "attribution" in result["note"]
    assert result["best_match"]["similarity"] <= 1.0


def test_levenshtein_properties():
    assert normalized_levenshtein(["A", "B", "C"], ["A", "B", "C"]) == 1.0
    assert normalized_levenshtein(["A", "B"], ["B", "A"]) == 0.0  # 2 substitutions
    assert normalized_levenshtein(["A"], ["B"]) == 0.0
    assert normalized_levenshtein([], ["A", "B"]) == 0.0
    assert normalized_levenshtein([], []) == 1.0


def test_no_confident_match_below_threshold():
    partial = DIGITAL_ARREST_CHAT[:2]  # only 2 of 5 stages
    result = classify_case(partial, PLAYBOOKS, config={"match_threshold": 0.95})
    assert result["verdict"] in ("NO_CONFIDENT_MATCH", "MATCHED")
    if result["verdict"] == "MATCHED":
        assert result["best_match"]["similarity"] >= 0.95


def test_playbook_library_validation():
    import json, tempfile
    bad = {"playbooks": [{"name": "X", "stages": [], "detectors": {}}]}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(bad, fh)
        path = fh.name
    try:
        with pytest.raises(ValueError):
            load_playbooks(path)
    finally:
        os.unlink(path)
