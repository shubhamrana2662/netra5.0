"""Feature 11 tests — determinism, ground-truth integrity, cross-engine alignment."""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEATURES_ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from engine import BenchmarkGenerator, load_json  # noqa: E402


def _load_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # dataclasses resolves annotations via sys.modules
    spec.loader.exec_module(mod)
    return mod


f2 = _load_module(
    "f2_contradiction",
    os.path.join(FEATURES_ROOT, "feature_02_contradiction", "engine.py"),
)

POOLS = os.path.join(HERE, "data", "pools.json")
TYPOLOGIES = os.path.join(HERE, "data", "typologies.json")


def make_gen(**cfg):
    return BenchmarkGenerator(load_json(POOLS), load_json(TYPOLOGIES), cfg or None)


def test_determinism_same_seed_identical_output():
    a = make_gen().generate_case("DIGITAL_ARREST", seed=1234)
    b = make_gen().generate_case("DIGITAL_ARREST", seed=1234)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_different_seeds_differ():
    a = make_gen().generate_case("DIGITAL_ARREST", seed=1)
    b = make_gen().generate_case("DIGITAL_ARREST", seed=2)
    assert a["case_id"] != b["case_id"]
    assert a["artifacts"]["whatsapp_export.txt"] != b["artifacts"]["whatsapp_export.txt"]


def test_unknown_typology_rejected():
    try:
        make_gen().generate_case("NO_SUCH_TYPE", seed=1)
    except KeyError as e:
        assert "NO_SUCH_TYPE" in str(e)
    else:
        raise AssertionError("expected KeyError")


def test_ground_truth_entities_appear_in_artifacts():
    case = make_gen().generate_case("DIGITAL_ARREST", seed=77)
    gt = case["ground_truth"]
    chat = case["artifacts"]["whatsapp_export.txt"]
    bank_blob = json.dumps(case["artifacts"]["bank_statement.csv"])
    cdr_blob = json.dumps(case["artifacts"]["cdr.csv"])
    for ent in gt["entities"]:
        if ent["phone"]:
            assert ent["phone"] in chat or ent["phone"] in cdr_blob, \
                f"phone {ent['phone']} missing from artifacts"
        if ent["account"]:
            assert ent["account"] in bank_blob, f"account {ent['account']} missing"


def test_planted_hidden_link_never_co_occurs():
    case = make_gen().generate_case("DIGITAL_ARREST", seed=88)
    gt = case["ground_truth"]
    phone_value, account_value = gt["planted_hidden_links"][0]["pair"]
    chat = case["artifacts"]["whatsapp_export.txt"]
    bank_blob = json.dumps(case["artifacts"]["bank_statement.csv"])
    cdr_blob = json.dumps(case["artifacts"]["cdr.csv"])
    assert phone_value in chat or phone_value in cdr_blob
    assert account_value in bank_blob
    # the constraint: the planted pair never appears in the SAME artifact
    assert account_value not in chat and account_value not in cdr_blob
    assert phone_value not in bank_blob


def test_money_flow_edges_conserve_at_first_hop():
    case = make_gen().generate_case("INVESTMENT_TASK", seed=5)
    edges = case["ground_truth"]["money_flow_edges"]
    assert edges, "no money flow generated"
    total_out = sum(e["amount"] for e in edges if e["from"].startswith("victim"))
    total_l1_in = sum(e["amount"] for e in edges if e["to"].startswith("l1"))
    assert total_out == total_l1_in


def test_generated_bank_ledger_is_arithmetically_clean():
    """Cross-feature alignment: every generated account's rows must pass
    Feature 2's ledger audit (running balances consistent, no fake noise)."""
    case = make_gen(ocr_pct=0).generate_case("DIGITAL_ARREST", seed=42)
    rows = case["artifacts"]["bank_statement.csv"]
    by_account: dict[str, list[dict]] = {}
    for r in rows:
        by_account.setdefault(r["account"], []).append(r)
    assert by_account, "no bank rows generated"
    for account, acct_rows in by_account.items():
        findings = f2.ledger_audit(acct_rows)
        assert findings == [], f"account {account}: {findings}"


def test_ocr_noise_applied_and_recorded():
    case = make_gen(ocr_pct=0.5).generate_case("DIGITAL_ARREST", seed=99)
    gt = case["ground_truth"]
    clean = json.dumps(case["artifacts"]["bank_statement.csv"])
    noisy = json.dumps(case["artifacts"]["bank_statement_noisy.csv"])
    assert gt["ocr_noise_applied"] is True
    assert clean != noisy  # at 50% noise on ~20 rows, difference is certain


def test_zero_noise_produces_identical_clean_and_noisy():
    case = make_gen(ocr_pct=0).generate_case("DIGITAL_ARREST", seed=7)
    assert case["artifacts"]["bank_statement.csv"] == \
           case["artifacts"]["bank_statement_noisy.csv"]
    assert case["ground_truth"]["ocr_noise_applied"] is False


def test_dropped_cdr_row_recorded_in_ground_truth():
    case = make_gen(cdr_drop_pct=0.5).generate_case("INVESTMENT_TASK", seed=11)
    planted = case["ground_truth"]["planted_contradictions"][0]
    assert planted["kind"] == "DROPPED_CDR_ROWS"
    assert planted["count"] == 1
    dropped = planted["rows"][0]
    cdr_blob = json.dumps(case["artifacts"]["cdr.csv"])
    assert json.dumps(dropped) not in cdr_blob or dropped not in case["artifacts"]["cdr.csv"]
