# Feature 10 — Network Replay (CTDG frame slicer, isolated build)

Converts timestamped case events into an ordered frame array for the
time-scrubber UI: `active_nodes(t)`, `active_edges(t)` (edges appear at their
event time and never vanish), `opacity = exp(−age/τ)` (older edges fade), and
a `burst` flag when event density in a sliding window crosses a threshold —
the visual signature of coordination.

Pure function: events in → frames out. All knobs are config
(`step_seconds`, `tau_seconds`, `burst_window_s`, `burst_threshold`,
`max_frames`). Rendering/playback belongs to the frontend (React Flow is
comfortable to ~1000 nodes; per-case graphs are bounded well below that).

Bugs the tests caught and fixed: a `partition` unpacking error that corrupted
edge endpoints, frames ending before the last event (off-by-one on the span →
ceiling), and single-instant spans emitting two frames.

Run: `D:/PROJECTS/cyber_v3/features/.venv/Scripts/python.exe -m pytest tests/ -v` — 10 passed.

Integration: `GET /replay/{case_id}?t_start&t_end&step_ms` returns the frame
array; frontend scrubber maps frame index → React Flow state, burst frames
pulse crimson, playback speed = frames/sec. Events come from
`evidence_events` ordered by `event_timestamp`.
