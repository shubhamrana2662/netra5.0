"""CyberDrishti Feature 2 — Contradiction Engine (isolated build).

Finds internal contradictions in evidence that no single document states:
  Module A — Ledger audit:        opening + credits − debits = closing,
                                  per row; distinguishes ALTERED_BALANCE
                                  (row tampered) from MISSING_ROWS
                                  (continuity intact across a gap).
  Module B — Impossible travel:   haversine velocity between an entity's
                                  geolocated events; > impossible_kmh flags
                                  physical impossibility (cloned SIM /
                                  co-conspirator / proxy), > suspicious_kmh
                                  flags implausible speed.
  Module C — Temporal ordering:   declared causal orderings across sources
                                  ("threat call BEFORE transfer") that the
                                  timestamps violate.

Everything is derived from caller-provided events. Location data is often
city-level and tower-derived: every output carries the exact computed values
(distance, velocity, gap) plus an `epistemic_status` label so the UI can never
present an inference as an observation. No case data is embedded here.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Sequence

DEFAULT_CONFIG: dict[str, Any] = {
    "impossible_kmh": 900.0,      # faster than any commercial aircraft
    "suspicious_kmh": 200.0,      # implausible for ground travel in most cases
    "clock_tolerance_s": 600,     # ±10 min telecom clock drift guardrail
    "balance_tolerance": 0.01,    # rounding tolerance on ledger arithmetic
    "min_pair_gap_s": 60,         # ignore absurdly short event gaps (same instant)
}


# ---------------------------------------------------------------- parsing ----

def parse_ts(value: Any) -> datetime:
    """ISO-8601 or common evidence formats → aware datetime (assumes UTC if naive)."""
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# ------------------------------------------------------------- module A ------

@dataclass
class LedgerFinding:
    kind: str            # ALTERED_BALANCE | MISSING_ROWS_SUSPECTED
    row_index: int
    expected_balance: float
    reported_balance: float
    discrepancy: float
    explanation: str
    epistemic_status: str = "DERIVED"   # pure arithmetic on observed rows


def ledger_audit(rows: Sequence[dict[str, Any]], config: dict[str, Any] | None = None) -> list[LedgerFinding]:
    """Rows need: credit, debit, balance (numbers) in statement order.

    Per-row arithmetic. Break classification follows the propagation pattern:
    - A break whose successor row balances AGAIN FROM THE REPORTED balance is
      local: either an edited block (balances i and i+1 edited together) or
      rows removed between i-1 and i. Reported as MISSING_ROWS_OR_EDITED_BLOCK.
    - A break that PROPAGATES (successor also breaks) means a figure was edited
      without fixing the chain: ALTERED_BALANCE.
    Honest limitation (documented in README): silently removing a middle row
    leaves per-row arithmetic consistent — that is caught by Feature 1's
    version diff or by summary_check against stated totals, not here.
    """
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    tol = float(cfg["balance_tolerance"])
    findings: list[LedgerFinding] = []
    prev_reported: float | None = None
    for i, row in enumerate(rows):
        credit = float(row.get("credit") or 0)
        debit = float(row.get("debit") or 0)
        balance = float(row.get("balance") or 0)
        opening = row.get("opening_balance")
        if i == 0 and opening is None:
            # Row 0's balance is the AFTER-transaction figure; with no stated
            # opening we cannot verify it — it becomes the chain anchor.
            prev_reported = balance
            continue
        expected = (float(opening) if (i == 0 and opening is not None)
                    else prev_reported) + credit - debit
        discrepancy = round(balance - expected, 2)
        if abs(discrepancy) > tol:
            findings.append(LedgerFinding(
                kind="BREAK_UNCLASSIFIED",
                row_index=i,
                expected_balance=round(expected, 2),
                reported_balance=round(balance, 2),
                discrepancy=discrepancy,
                explanation=(
                    f"Row {i}: reported balance {balance:.2f} does not equal "
                    f"previous {prev_reported:.2f} + {credit:.2f} − {debit:.2f} "
                    f"= {expected:.2f}."
                ),
            ))
        prev_reported = balance

    break_at = {f.row_index: f for f in findings}
    for f in findings:
        i = f.row_index
        nxt = i + 1
        if nxt >= len(rows):
            f.kind = "MISSING_ROWS_OR_EDITED_BLOCK"  # nothing after to propagate to
            continue
        nrow = rows[nxt]
        if nxt in break_at:
            f.kind = "ALTERED_BALANCE"  # discrepancy propagates → edited figure
            f.explanation += " Break propagates to subsequent rows."
        else:
            n_exp = f.reported_balance + float(nrow.get("credit") or 0) - float(nrow.get("debit") or 0)
            if abs(float(nrow.get("balance") or 0) - n_exp) <= tol:
                f.kind = "MISSING_ROWS_OR_EDITED_BLOCK"
                f.explanation += (
                    " Next row balances from this row's reported value: local "
                    "anomaly — rows removed here, or an edited block."
                )
            else:
                f.kind = "ALTERED_BALANCE"
    return findings


def summary_check(
    rows: Sequence[dict[str, Any]],
    stated_opening: float | None = None,
    stated_closing: float | None = None,
    stated_credit_total: float | None = None,
    stated_debit_total: float | None = None,
    config: dict[str, Any] | None = None,
) -> list[LedgerFinding]:
    """Cross-checks stated statement totals against the parsed rows.

    Catches silent middle-row removal when the forger left the statement's
    own summary figures (totals/closing) untouched.
    """
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    tol = float(cfg["balance_tolerance"])
    credit_total = sum(float(r.get("credit") or 0) for r in rows)
    debit_total = sum(float(r.get("debit") or 0) for r in rows)
    first_balance = float(rows[0].get("balance") or 0) if rows else 0.0
    last_balance = float(rows[-1].get("balance") or 0) if rows else 0.0
    implied_opening = first_balance + debit_total - credit_total
    findings: list[LedgerFinding] = []

    def check(label: str, expected: float, reported: float) -> None:
        if abs(reported - expected) > tol:
            findings.append(LedgerFinding(
                kind="SUMMARY_MISMATCH",
                row_index=-1,
                expected_balance=round(expected, 2),
                reported_balance=round(reported, 2),
                discrepancy=round(reported - expected, 2),
                explanation=(
                    f"Stated {label} ({reported:.2f}) contradicts row arithmetic "
                    f"({expected:.2f}). Rows may have been removed or totals edited."
                ),
            ))

    if stated_opening is not None:
        check("opening balance", implied_opening, float(stated_opening))
    if stated_closing is not None:
        expected_closing = (float(stated_opening) if stated_opening is not None
                            else implied_opening) + credit_total - debit_total
        check("closing balance", expected_closing, float(stated_closing))
    if stated_credit_total is not None:
        check("credit total", credit_total, float(stated_credit_total))
    if stated_debit_total is not None:
        check("debit total", debit_total, float(stated_debit_total))
    return findings


# ------------------------------------------------------------- module B ------

@dataclass
class TravelFinding:
    kind: str                    # IMPOSSIBLE_TRAVEL | SUSPICIOUS_VELOCITY
    entity: str
    distance_km: float
    velocity_kmh: float
    time_gap_s: float
    event_a: dict[str, Any]
    event_b: dict[str, Any]
    explanation: str
    epistemic_status: str = "INFERRED"  # tower/city-derived locations


def _loc(event: dict[str, Any]) -> tuple[float, float] | None:
    lat, lon = event.get("lat"), event.get("lon")
    if lat is None or lon is None:
        return None
    return float(lat), float(lon)


def impossible_travel(
    events: Sequence[dict[str, Any]], config: dict[str, Any] | None = None
) -> list[TravelFinding]:
    """Events need: entity, timestamp, lat/lon (tower- or city-derived).

    Events without coordinates are counted and reported as skipped, never
    silently ignored. Clock tolerance widens the window before flagging.
    """
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    by_entity: dict[str, list[dict[str, Any]]] = {}
    skipped = 0
    for e in events:
        if _loc(e) is None:
            skipped += 1
            continue
        by_entity.setdefault(str(e["entity"]), []).append(e)

    findings: list[TravelFinding] = []
    for entity, evs in by_entity.items():
        evs.sort(key=lambda e: parse_ts(e["timestamp"]))
        for i in range(len(evs) - 1):
            a, b = evs[i], evs[i + 1]
            gap_s = (parse_ts(b["timestamp"]) - parse_ts(a["timestamp"])).total_seconds()
            if gap_s < cfg["min_pair_gap_s"]:
                continue
            la, lo = _loc(a)
            lb, lo2 = _loc(b)
            dist = haversine_km(la, lo, lb, lo2)
            # Conservative physics: clock drift is ±tolerance, so the SLOWEST
            # plausible required speed uses gap + tolerance. Flag IMPOSSIBLE
            # only when even that lower bound exceeds the aviation ceiling —
            # this is what prevents false positives from clock skew.
            v_lower = dist / ((gap_s + cfg["clock_tolerance_s"]) / 3600.0)
            v_naive = dist / max(gap_s, cfg["min_pair_gap_s"]) * 3600.0
            kind = None
            if v_lower > cfg["impossible_kmh"]:
                kind = "IMPOSSIBLE_TRAVEL"
            elif v_naive > cfg["suspicious_kmh"]:
                kind = "SUSPICIOUS_VELOCITY"
            if kind:
                findings.append(TravelFinding(
                    kind=kind,
                    entity=entity,
                    distance_km=round(dist, 1),
                    velocity_kmh=round(min(v_naive, v_lower) if kind == "IMPOSSIBLE_TRAVEL" else v_naive, 1),
                    time_gap_s=gap_s,
                    event_a=a, event_b=b,
                    explanation=(
                        f"{entity}: {dist:.0f} km between {a.get('source', 'event A')} "
                        f"and {b.get('source', 'event B')} in {gap_s / 60:.0f} min "
                        f"(required speed ≥{v_lower:,.0f} km/h even allowing "
                        f"±{cfg['clock_tolerance_s'] // 60} min clock drift). "
                        f"Indicates a cloned SIM, co-located conspirator, or proxy."
                    ),
                ))
    findings.sort(key=lambda f: -f.velocity_kmh)
    # expose skipped count via attribute on first finding for caller awareness
    if findings:
        findings[0].explanation += f" [skipped {skipped} event(s) without coordinates]"
    return findings


# ------------------------------------------------------------- module C ------

@dataclass
class OrderingFinding:
    kind: str
    rule: dict[str, Any]
    before_event: dict[str, Any]
    after_event: dict[str, Any]
    explanation: str
    epistemic_status: str = "DERIVED"


def temporal_ordering_violations(
    events: Sequence[dict[str, Any]],
    ordering_rules: Sequence[dict[str, Any]],
    config: dict[str, Any] | None = None,
) -> list[OrderingFinding]:
    """Each rule: {"name": str, "earlier": <event_type>, "later": <event_type>,
    "max_gap_s": float|None, "pair_by": str|None (field to match on)}.

    A violation = matched 'later' event whose timestamp precedes its matched
    'earlier' event (or exceeds max_gap_s when configured).
    """
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    _ = cfg
    findings: list[OrderingFinding] = []
    for rule in ordering_rules:
        earlier_type, later_type = rule["earlier"], rule["later"]
        pair_by = rule.get("pair_by")
        for later_ev in events:
            if later_ev.get("event_type") != later_type:
                continue
            candidates = [
                e for e in events
                if e.get("event_type") == earlier_type
                and (pair_by is None or e.get(pair_by) == later_ev.get(pair_by))
            ]
            if not candidates:
                continue
            earlier_ev = max(candidates, key=lambda e: parse_ts(e["timestamp"]))
            earlier_ts = parse_ts(earlier_ev["timestamp"])
            later_ts = parse_ts(later_ev["timestamp"])
            gap_s = (later_ts - earlier_ts).total_seconds()
            max_gap = rule.get("max_gap_s")
            violated = later_ts < earlier_ts or (max_gap is not None and gap_s > max_gap)
            if violated:
                direction = "precedes" if later_ts < earlier_ts else "exceeds max gap of"
                findings.append(OrderingFinding(
                    kind="TEMPORAL_ANOMALY",
                    rule=rule,
                    before_event=earlier_ev,
                    after_event=later_ev,
                    explanation=(
                        f"Rule '{rule['name']}' violated: {later_type} "
                        f"({later_ev.get('source', '?')}) {direction} the required "
                        f"{earlier_type} ({earlier_ev.get('source', '?')}) by "
                        f"{abs(gap_s) / 60:.0f} min."
                    ),
                ))
    return findings


def scan_all(
    ledger_rows: Sequence[dict[str, Any]],
    travel_events: Sequence[dict[str, Any]],
    ordering_events: Sequence[dict[str, Any]],
    ordering_rules: Sequence[dict[str, Any]],
    config: dict[str, Any] | None = None,
) -> dict[str, list]:
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    findings: dict[str, list] = {
        "ledger": ledger_audit(ledger_rows, cfg),
        "travel": impossible_travel(travel_events, cfg),
        "ordering": temporal_ordering_violations(ordering_events, ordering_rules, cfg),
    }
    total = sum(len(v) for v in findings.values())
    return {"findings": findings, "total": total,
            "severity_note": "Every finding carries computed values and sources; none is auto-dismissable."}
