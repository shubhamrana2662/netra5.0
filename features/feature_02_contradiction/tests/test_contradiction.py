"""Feature 2 tests — synthetic ledgers/routes only; thresholds via config."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import (
    haversine_km, impossible_travel, ledger_audit, parse_ts, summary_check,
    temporal_ordering_violations,
)

# Deloitte-free, case-free synthetic fixtures -------------------------------

def clean_ledger():
    return [
        {"credit": 0, "debit": 100, "balance": 900, "opening_balance": 1000},
        {"credit": 500, "debit": 0, "balance": 1400},
        {"credit": 0, "debit": 400, "balance": 1000},
    ]


def forged_ledger_altered():
    rows = clean_ledger()
    rows[1]["balance"] = 1500  # edited figure, next row still follows old chain
    return rows


def ledger_with_removed_row():
    # removing row 2 (credit 500 → 1400) makes row 3 break once, then chain continues
    return [
        {"credit": 0, "debit": 100, "balance": 900, "opening_balance": 1000},
        {"credit": 0, "debit": 400, "balance": 500},
    ]


def geo_events():
    # Delhi ~ (28.61, 77.21), Bengaluru ~ (12.97, 77.59): ~1740 km apart
    return [
        {"entity": "PHONE-1", "timestamp": "2026-04-22T11:15:00+05:30",
         "lat": 28.61, "lon": 77.21, "source": "cdr:DEL-TWR-021"},
        {"entity": "PHONE-1", "timestamp": "2026-04-22T11:30:00+05:30",
         "lat": 12.97, "lon": 77.59, "source": "atm:BLR"},
        # same-city second pair: plausible
        {"entity": "PHONE-2", "timestamp": "2026-04-22T09:00:00+05:30",
         "lat": 28.61, "lon": 77.21, "source": "cdr:DEL-TWR-005"},
        {"entity": "PHONE-2", "timestamp": "2026-04-22T09:40:00+05:30",
         "lat": 28.70, "lon": 77.30, "source": "cdr:DEL-TWR-009"},
    ]


# --- Module A: ledger --------------------------------------------------------

def test_clean_ledger_yields_no_findings():
    assert ledger_audit(clean_ledger()) == []


def test_altered_balance_flagged_with_exact_values():
    findings = ledger_audit(forged_ledger_altered())
    # editing row 1's balance without fixing row 2 → the break PROPAGATES
    assert len(findings) == 2
    f = findings[0]
    assert f.row_index == 1
    assert f.kind == "ALTERED_BALANCE"
    assert f.expected_balance == 1400.00
    assert f.reported_balance == 1500.00
    assert f.discrepancy == 100.00
    assert f.epistemic_status == "DERIVED"


def test_removed_row_is_arithmetic_clean_but_caught_by_summary():
    # removing the middle row leaves per-row arithmetic consistent — the honest
    # limitation of per-row audit; the statement's own closing total betrays it.
    rows = ledger_with_removed_row()
    assert ledger_audit(rows) == []
    findings = summary_check(rows, stated_opening=1000, stated_closing=1000)
    # BOTH stated anchors contradict the row arithmetic — twice the evidence
    assert len(findings) == 2
    assert all(f.kind == "SUMMARY_MISMATCH" for f in findings)
    assert all("removed" in f.explanation for f in findings)


def test_edited_block_classified_as_local_anomaly():
    # forger edits balances of rows 1 AND 2 together (chain stays consistent
    # afterwards): break at row 1 whose successor balances from reported value
    rows = [
        {"credit": 0, "debit": 100, "balance": 900, "opening_balance": 1000},
        {"credit": 500, "debit": 0, "balance": 1500},   # inflated (+100)
        {"credit": 0, "debit": 400, "balance": 1100},   # follows the inflated 1500
    ]
    findings = ledger_audit(rows)
    assert len(findings) == 1
    assert findings[0].kind == "MISSING_ROWS_OR_EDITED_BLOCK"


def test_ledger_tolerates_rounding_within_tolerance():
    rows = clean_ledger()
    rows[2]["balance"] = 1000.005  # under default 0.01 tolerance
    assert ledger_audit(rows) == []


# --- Module B: travel ---------------------------------------------------------

def test_impossible_travel_delhi_to_bengaluru_in_15min():
    findings = impossible_travel(geo_events())
    assert len(findings) == 1
    f = findings[0]
    assert f.kind == "IMPOSSIBLE_TRAVEL"
    assert f.entity == "PHONE-1"
    assert 1700 < f.distance_km < 1800
    # raw required speed ≈ 6,960 km/h; ≥4,000 even with the ±10 min tolerance
    assert f.velocity_kmh > 3500
    assert f.epistemic_status == "INFERRED"
    assert "cdr:DEL-TWR-021" in f.explanation and "atm:BLR" in f.explanation


def test_plausible_same_city_travel_not_flagged():
    findings = impossible_travel(geo_events())
    entities = {f.entity for f in findings}
    assert "PHONE-2" not in entities


def test_clock_tolerance_widens_window_before_flagging():
    # 200 km in 10 min → 1200 km/h naive; with ±10 min tolerance, effective
    # gap floors at min_pair_gap_s=60s → still impossible; but a 12 min trip
    # to a place 30 km away: naive 150 km/h (fine); tolerance doesn't flag.
    events = [
        {"entity": "P", "timestamp": "2026-04-22T10:00:00+05:30",
         "lat": 28.61, "lon": 77.21, "source": "cdr"},
        {"entity": "P", "timestamp": "2026-04-22T10:12:00+05:30",
         "lat": 28.85, "lon": 77.30, "source": "atm"},  # ~30 km
    ]
    assert impossible_travel(events) == []


def test_events_without_coordinates_are_counted_not_silently_dropped():
    events = geo_events() + [
        {"entity": "PHONE-1", "timestamp": "2026-04-22T12:00:00+05:30",
         "source": "ipdr"}  # no lat/lon
    ]
    findings = impossible_travel(events)
    assert len(findings) == 1  # same as before; no crash
    assert "skipped 1 event(s)" in findings[0].explanation


# --- Module C: ordering --------------------------------------------------------

def test_threat_call_after_transfer_is_a_violation():
    events = [
        {"event_type": "threat_call", "timestamp": "2026-04-22T12:30:00+05:30",
         "pair_by": "victim", "source": "cdr"},
        {"event_type": "transfer", "timestamp": "2026-04-22T10:15:00+05:30",
         "pair_by": "victim", "source": "bank"},
    ]
    rules = [{"name": "coercion-then-transfer",
              "earlier": "threat_call", "later": "transfer", "pair_by": "victim"}]
    findings = temporal_ordering_violations(events, rules)
    assert len(findings) == 1
    assert "precedes" in findings[0].explanation


def test_correct_ordering_and_max_gap_enforced():
    events = [
        {"event_type": "threat_call", "timestamp": "2026-04-22T10:00:00+05:30",
         "pair_by": "victim", "source": "cdr"},
        {"event_type": "transfer", "timestamp": "2026-04-22T10:05:00+05:30",
         "pair_by": "victim", "source": "bank"},
    ]
    rules = [{"name": "coercion-then-transfer", "earlier": "threat_call",
              "later": "transfer", "pair_by": "victim", "max_gap_s": 120}]
    # correct direction but gap (5 min) exceeds max_gap_s=2 min → violation
    findings = temporal_ordering_violations(events, rules)
    assert len(findings) == 1
    assert "exceeds max gap" in findings[0].explanation
    # and with a generous max_gap → clean
    rules[0]["max_gap_s"] = 600
    assert temporal_ordering_violations(events, rules) == []


# --- Utilities ------------------------------------------------------------------

def test_haversine_known_distance():
    # Delhi → Mumbai ≈ 1150 km; allow generous band for coordinate rounding
    d = haversine_km(28.61, 77.21, 19.07, 72.87)
    assert 1100 < d < 1200


def test_parse_ts_handles_z_and_naive():
    assert parse_ts("2026-04-22T11:15:00Z").tzinfo is not None
    assert parse_ts("2026-04-22T11:15:00").tzinfo is not None
    assert parse_ts("2026-04-22 11:15:00+05:30") == parse_ts("2026-04-22T11:15:00+05:30")
