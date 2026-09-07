"""Feature 8 tests — freeze semantics, conservation, honesty labels."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import simulate_freeze


def chain():
    return [
        {"from": "V", "to": "M1", "amount": 500000, "timestamp": "2026-04-22T10:20:00+05:30"},
        {"from": "M1", "to": "M2a", "amount": 200000, "timestamp": "2026-04-22T10:31:00+05:30"},
        {"from": "M1", "to": "M2b", "amount": 250000, "timestamp": "2026-04-22T10:33:00+05:30"},
        {"from": "M2a", "to": "ATM", "amount": 180000, "timestamp": "2026-04-22T10:45:00+05:30"},
    ]


def test_no_freeze_preserves_nothing():
    out = simulate_freeze(chain(), "___none___", "2099-01-01T00:00:00+05:30")
    assert out["preserved_total"] == 0
    assert out["completed_transfers"] == 4


def test_freeze_on_m1_before_outflow_preserves_balance():
    # M1 frozen at 10:25: the 500k arrives at 10:20 (before freeze, completes),
    # outflows at 10:31/10:33 are blocked → 450k preserved at M1
    out = simulate_freeze(chain(), "M1", "2026-04-22T10:25:00+05:30")
    assert out["preserved_total"] == 450000
    assert out["preserved_by_account"] == {"M1": 450000}
    assert len(out["blocked_out_events"]) == 2
    assert out["assessment_type"] == "APPROXIMATED_LOWER_BOUND"


def test_freeze_on_receiver_stops_incoming_funds():
    # freeze M2a before the victim's money reaches it via M1? M1→M2a happens at
    # 10:31; freeze M2a at 10:30 → that transfer stops and is preserved.
    out = simulate_freeze(chain(), "M2a", "2026-04-22T10:30:00+05:30")
    assert out["preserved_total"] == 200000
    assert out["preserved_by_account"] == {"M2a": 200000}
    assert any(e["reason"] == "receiver frozen" for e in out["stopped_in_events"])
    # but M2a→ATM at 10:45 is now a blocked outflow from a frozen account
    assert any(e["from"] == "M2a" for e in out["blocked_out_events"])


def test_freeze_after_all_activity_preserves_nothing():
    out = simulate_freeze(chain(), "M1", "2026-04-22T23:00:00+05:30")
    assert out["preserved_total"] == 0
    assert out["completed_transfers"] == 4


def test_earliest_freeze_catches_everything_downstream():
    out = simulate_freeze(chain(), "M1", "2026-04-22T00:00:00+05:30")
    # the victim→M1 transfer itself is stopped (receiver frozen)
    assert out["preserved_total"] == 500000


def test_caveats_always_present_and_honest():
    out = simulate_freeze(chain(), "M1", "2026-04-22T10:25:00+05:30")
    assert any("NOT admissible proof" in c for c in out["caveats"])
    assert out["epistemic_status"] == "APPROXIMATED"


def test_out_of_order_input_is_sorted_internally():
    shuffled = list(reversed(chain()))
    out = simulate_freeze(shuffled, "M1", "2026-04-22T10:25:00+05:30")
    assert out["preserved_total"] == 450000
