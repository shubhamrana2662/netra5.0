"""CyberDrishti Feature 7 — MO Fingerprinting (isolated build).

Represents a case as an ordered sequence of behavioral stage tokens
(a crime script: LURE → ISOLATION → EXTRACTION → LAYERING → DISPOSAL), built
by running per-stage detector regexes over the chat transcript, then matches
that sequence against a playbook library (data/playbooks.json) using
normalized Levenshtein edit distance on the stage tokens.

Honesty rules:
- Output is a SIMILARITY score in [0,1] with the per-stage alignment shown —
  never a "96% match with Syndicate #11" (no verified national syndicate
  registry exists to claim that against).
- If no playbook exceeds `match_threshold`, the engine says "no confident
  match" instead of returning a best guess.
- Every matched stage cites the message lines that triggered its detector.
- Playbooks are data only; detectors and stage lists are never in code.
"""
from __future__ import annotations

import json
import re
from typing import Any, Sequence

DEFAULT_CONFIG: dict[str, Any] = {
    "match_threshold": 0.60,   # normalized similarity to count as confident
    "max_stage_gap_lines": 40, # detector hits further apart start a new occurrence
}


def load_playbooks(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        lib = json.load(fh)
    for pb in lib["playbooks"]:
        if not pb.get("stages") or not pb.get("detectors"):
            raise ValueError(f"playbook '{pb.get('name')}' needs stages + detectors")
    return lib


def normalized_levenshtein(a: Sequence[str], b: Sequence[str]) -> float:
    """1 − edit_distance / max(len) — 1.0 identical, 0.0 fully different."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    dist = prev[-1]
    return 1.0 - dist / max(len(a), len(b))


def build_behavioral_trace(
    messages: Sequence[dict[str, Any]],
    playbooks_lib: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """messages: [{line_no, sender, text, timestamp?}]. Detector hits are
    collected across ALL playbooks' detectors (a stage token is playbook
    vocabulary, so trace building is playbook-agnostic)."""
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    detector_map: dict[str, list[tuple[str, re.Pattern]]] = {}
    for pb in playbooks_lib["playbooks"]:
        for stage, patterns in pb["detectors"].items():
            for p in patterns:
                detector_map.setdefault(stage, []).append(
                    (pb["name"], re.compile(p, re.IGNORECASE))
                )

    trace: list[dict[str, Any]] = []
    last_line_by_stage: dict[str, int] = {}
    for msg in messages:
        text = str(msg.get("text", ""))
        for stage, patterns in detector_map.items():
            for source, pattern in patterns:
                m = pattern.search(text)
                if m:
                    ln = int(msg.get("line_no", 0))
                    prev = last_line_by_stage.get(stage)
                    if prev is not None and ln - prev > cfg["max_stage_gap_lines"]:
                        # far-apart repeat: keep the later occurrence in trace
                        trace = [t for t in trace if t["stage"] != stage or
                                 t["line_no"] > ln]
                    last_line_by_stage[stage] = ln
                    trace.append({
                        "stage": stage,
                        "line_no": ln,
                        "matched_text": m.group(0),
                        "sender": msg.get("sender"),
                        "source_playbook": source,
                    })
                    break  # one hit per stage per message
    trace.sort(key=lambda t: t["line_no"])
    # dedupe: keep first occurrence per stage for the sequence
    seen: set[str] = set()
    sequence: list[dict[str, Any]] = []
    for t in trace:
        if t["stage"] not in seen:
            seen.add(t["stage"])
            sequence.append(t)
    return {"sequence": [t["stage"] for t in sequence],
            "evidence": sequence,
            "all_hits": trace}


def match_trace(
    behavioral_trace: dict[str, Any],
    playbooks_lib: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    observed = behavioral_trace["sequence"]
    scored = []
    for pb in playbooks_lib["playbooks"]:
        similarity = normalized_levenshtein(observed, pb["stages"])
        alignment = [
            {"stage": s, "in_playbook": s in pb["stages"],
             "observed_position": i + 1,
             "playbook_position": (pb["stages"].index(s) + 1) if s in pb["stages"] else None}
            for i, s in enumerate(observed)
        ]
        scored.append({
            "playbook": pb["name"],
            "source": pb.get("source", ""),
            "similarity": round(similarity, 4),
            "alignment": alignment,
            "epistemic_status": "PREDICTED",
        })
    scored.sort(key=lambda s: -s["similarity"])
    confident = [s for s in scored if s["similarity"] >= cfg["match_threshold"]]
    return {
        "observed_sequence": observed,
        "matches": scored,
        "best_match": confident[0] if confident else None,
        "verdict": ("MATCHED" if confident else
                    "NO_CONFIDENT_MATCH" if observed else "INSUFFICIENT_TRACE"),
        "note": ("Similarity of behavioral stage sequences — a screening aid, "
                 "not an attribution to a specific syndicate."),
    }


def classify_case(
    messages: Sequence[dict[str, Any]],
    playbooks_lib: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Per-playbook tracing: each playbook is traced against ITS OWN detectors
    only, so stages from unrelated playbooks never pollute a sequence and
    shared stage vocabulary is scored in each playbook's own context."""
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    per_playbook = []
    for pb in playbooks_lib["playbooks"]:
        trace = build_behavioral_trace(messages, {"playbooks": [pb]}, cfg)
        similarity = normalized_levenshtein(trace["sequence"], pb["stages"])
        per_playbook.append({
            "playbook": pb["name"],
            "source": pb.get("source", ""),
            "similarity": round(similarity, 4),
            "observed_sequence": trace["sequence"],
            "alignment": [
                {"stage": s, "in_playbook": s in pb["stages"],
                 "observed_position": i + 1,
                 "playbook_position": (pb["stages"].index(s) + 1) if s in pb["stages"] else None}
                for i, s in enumerate(trace["sequence"])
            ],
            "trace_evidence": trace["evidence"],
            "epistemic_status": "PREDICTED",
        })
    per_playbook.sort(key=lambda p: -p["similarity"])
    confident = [p for p in per_playbook if p["similarity"] >= cfg["match_threshold"]]
    best = confident[0] if confident else None
    return {
        "observed_sequence": best["observed_sequence"] if best else [],
        "matches": per_playbook,
        "best_match": best,
        "verdict": ("MATCHED" if confident else
                    "NO_CONFIDENT_MATCH" if any(p["observed_sequence"] for p in per_playbook)
                    else "INSUFFICIENT_TRACE"),
        "trace_evidence": best["trace_evidence"] if best else
        [h for p in per_playbook for h in p["trace_evidence"]],
        "note": ("Similarity of behavioral stage sequences — a screening aid, "
                 "not an attribution to a specific syndicate."),
    }
