"""CyberDrishti Feature 10 — Network Replay / CTDG frame slicer (isolated build).

Turns a case's timestamped events into an ordered array of graph frames for
the time-scrubber UI. A case network is a Continuous-Time Dynamic Graph:
G(t) = (V(t), E(t)) where an edge exists once its event has occurred. Frames
are the discrete sampling of that continuity:

  active_nodes(t) = {v : first_seen(v) <= t}
  active_edges(t) = {e : t_e <= t}
  edge_opacity(t) = exp(-(t - t_e) / tau)     (older edges fade, never vanish)

Burst windows (configurable density threshold over a sliding window) mark
frames as `burst: true` so the UI can pulse them — communication bursts are
the visual signature of coordination.

The engine is a pure function: events in, frames out. Rendering (React Flow,
opacity transitions, playback speed) belongs to the frontend. No case data,
no thresholds in code.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Sequence

DEFAULT_CONFIG: dict[str, Any] = {
    "step_seconds": 60,          # sampling interval between frames
    "tau_seconds": 1800.0,       # opacity decay constant (30 min half-life-ish)
    "max_frames": 2000,          # hard cap; caller should zoom t_start..t_end
    "burst_window_s": 900,       # sliding window for density
    "burst_threshold": 10,       # events within window → burst frame
}


def parse_ts(value: Any) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


@dataclass
class Frame:
    t: str
    nodes: list[str]
    edges: list[dict[str, Any]]
    burst: bool

    def to_dict(self) -> dict[str, Any]:
        return {"t": self.t, "nodes": self.nodes, "edges": self.edges, "burst": self.burst}


def _edge_id(u: str, v: str, te: datetime) -> str:
    return f"{u}->{v}@{te.isoformat()}"


def build_frames(
    events: Sequence[dict[str, Any]], config: dict[str, Any] | None = None
) -> list[Frame]:
    """Events need: timestamp, and either {u, v} for a relation event or
    {node} for a solo event (a solo event activates its node only)."""
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    if not events:
        return []

    parsed = sorted(
        ((parse_ts(e["timestamp"]), e) for e in events), key=lambda p: p[0]
    )
    t0, t_last = parsed[0][0], parsed[-1][0]
    step = max(int(cfg["step_seconds"]), 1)
    total_span_s = (t_last - t0).total_seconds()
    if total_span_s == 0:
        n_frames = 1  # single-instant case: one frame
    else:
        # ceiling: the final frame must land at/after the last event
        n_frames = min(math.ceil(total_span_s / step) + 1, int(cfg["max_frames"]))

    tau = float(cfg["tau_seconds"])
    burst_window = float(cfg["burst_window_s"])
    burst_threshold = int(cfg["burst_threshold"])

    frames: list[Frame] = []
    edge_start: dict[str, datetime] = {}
    active_nodes: set[str] = set()
    ei = 0  # next event index to apply

    for fi in range(n_frames):
        t = t0.timestamp() + fi * step
        t_dt = datetime.fromtimestamp(t, tz=t0.tzinfo)

        # apply all events with ts <= t
        while ei < len(parsed) and parsed[ei][0] <= t_dt:
            te, e = parsed[ei]
            if e.get("u") and e.get("v"):
                eid = _edge_id(e["u"], e["v"], te)
                if eid not in edge_start:
                    edge_start[eid] = te
            if e.get("u"):
                active_nodes.add(str(e["u"]))
            if e.get("v"):
                active_nodes.add(str(e["v"]))
            if e.get("node"):
                active_nodes.add(str(e["node"]))
            ei += 1

        visible_edges = []
        for eid, te in edge_start.items():
            age_s = (t_dt - te).total_seconds()
            opacity = math.exp(-age_s / tau) if age_s >= 0 else 0.0
            u, _, rest = eid.partition("->")
            v = rest.rsplit("@", 1)[0]
            visible_edges.append({"id": eid, "u": u, "v": v,
                                  "age_s": age_s,
                                  "opacity": round(opacity, 4)})

        burst = _is_burst(parsed, t_dt, burst_window, burst_threshold, ei)
        frames.append(Frame(
            t=t_dt.isoformat(),
            nodes=sorted(active_nodes),
            edges=visible_edges,
            burst=burst,
        ).to_dict())
    return frames


def _is_burst(
    parsed: list[tuple[datetime, dict[str, Any]]],
    t_dt: datetime,
    window_s: float,
    threshold: int,
    upto: int,
) -> bool:
    """True if >= threshold events occurred within window_s ending at t_dt."""
    lo = t_dt.timestamp() - window_s
    count = sum(1 for te, _ in parsed[:upto] if lo <= te.timestamp() <= t_dt.timestamp())
    return count >= threshold


def timeline_bounds(events: Sequence[dict[str, Any]]) -> dict[str, str | None]:
    if not events:
        return {"t_start": None, "t_end": None}
    times = [parse_ts(e["timestamp"]) for e in events]
    return {"t_start": min(times).isoformat(), "t_end": max(times).isoformat()}
