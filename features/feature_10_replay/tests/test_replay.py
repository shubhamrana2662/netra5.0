"""Feature 10 tests — frame semantics, decay, bursts, caps."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import DEFAULT_CONFIG, build_frames, parse_ts, timeline_bounds


def events():
    base = "2026-04-22T10:%02d:00+05:30"
    return [
        {"event_type": "call", "timestamp": base % 0, "u": "P1", "v": "P2"},
        {"event_type": "call", "timestamp": base % 5, "u": "P1", "v": "P3"},
        {"event_type": "transfer", "timestamp": base % 10, "u": "P2", "v": "M1", "amount": 50000},
        {"event_type": "transfer", "timestamp": base % 11, "u": "M1", "v": "M2", "amount": 49000},
    ]


def test_frames_cover_span_at_requested_step():
    frames = build_frames(events(), {"step_seconds": 60})
    # span 10:00→10:11 = 11 min → 12 frames at 60 s
    assert len(frames) == 12
    assert parse_ts(frames[0]["t"]) < parse_ts(frames[-1]["t"])


def test_edges_appear_only_after_their_event():
    frames = build_frames(events(), {"step_seconds": 60})
    f0 = frames[0]  # t = 10:00, first event exactly now
    assert any(e["u"] == "P1" and e["v"] == "P2" for e in f0["edges"])
    f_m2 = frames[3]  # 10:03 — M1→M2 event (10:11) not yet happened
    assert not any(e["v"] == "M2" for e in f_m2["edges"])
    f_last = frames[-1]
    assert any(e["v"] == "M2" for e in f_last["edges"])


def test_opacity_decays_monotonically_for_old_edges():
    frames = build_frames(events(), {"step_seconds": 60, "tau_seconds": 300})
    target = [f for f in frames if any(e["u"] == "P1" and e["v"] == "P2" for e in f["edges"])]
    opacities = [next(e["opacity"] for e in f["edges"] if e["u"] == "P1" and e["v"] == "P2")
                 for f in target]
    assert opacities[0] == 1.0
    assert all(a > b for a, b in zip(opacities, opacities[1:])), opacities


def test_nodes_persist_once_active():
    frames = build_frames(events(), {"step_seconds": 60})
    for i in range(1, len(frames)):
        assert set(frames[i - 1]["nodes"]) <= set(frames[i]["nodes"])


def test_burst_flag_when_density_exceeded():
    dense = [{"event_type": "call",
              "timestamp": f"2026-04-22T10:{m // 6:02d}:{(m % 6) * 10:02d}+05:30",
              "u": "P1", "v": "P2"} for m in range(12)]  # 12 calls in ~11 min
    frames = build_frames(dense, {"step_seconds": 60, "burst_window_s": 900,
                                  "burst_threshold": 10})
    assert any(f["burst"] for f in frames)
    # sparse events never burst
    calm = build_frames(events(), {"step_seconds": 60})
    assert not any(f["burst"] for f in calm)


def test_max_frames_cap_prevents_runaway():
    many = events() * 500  # long span
    cfg = {"step_seconds": 1, "max_frames": 50}
    frames = build_frames(many, cfg)
    assert len(frames) <= 50


def test_empty_events_return_empty_and_bounds_none():
    assert build_frames([]) == []
    assert timeline_bounds([]) == {"t_start": None, "t_end": None}


def test_solo_events_activate_nodes_without_edges():
    solo = [
        {"event_type": "note", "timestamp": "2026-04-22T10:00:00+05:30", "node": "N1"},
        {"event_type": "note", "timestamp": "2026-04-22T10:02:00+05:30", "node": "N2"},
    ]
    frames = build_frames(solo, {"step_seconds": 60})
    assert frames[-1]["nodes"] == ["N1", "N2"]
    assert all(f["edges"] == [] for f in frames)


def test_single_instant_span_emits_one_frame():
    one = [{"event_type": "call", "timestamp": "2026-04-22T10:00:00+05:30",
            "u": "A", "v": "B"}]
    frames = build_frames(one)
    assert len(frames) == 1


def test_timeline_bounds():
    b = timeline_bounds(events())
    assert b["t_start"].startswith("2026-04-22T10:00")
    assert b["t_end"].startswith("2026-04-22T10:11")
