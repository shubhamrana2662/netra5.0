"""CyberDrishti Feature 8 — Counterfactual "What-If Freeze" Simulation.

Replays the case's timed money-flow (victim → mule layers → off-ramps) under a
hypothetical intervention: "account X is frozen at time T". Deterministic
discrete-event replay — network-interdiction style, no do-calculus library
required:

  for each transfer in chronological order:
    sender blocked at t  → transfer cannot leave        (funds remain frozen)
    receiver blocked at t → funds stop there            (PRESERVED)
    otherwise            → transfer completes

Output labels itself APPROXIMATED and reports a LOWER BOUND on savings: flows
beyond the uploaded statements (cash withdrawal chains, hawala, off-ramp
activity not in evidence) are unobservable, so the engine cannot claim "this
is what would have been saved" — and it is certainly not "admissible proof of
negligence". It is decision-support with bounds.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Sequence

DEFAULT_CONFIG: dict[str, Any] = {
    "max_events": 100000,
}


def _ts(value: Any) -> datetime:
    dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def simulate_freeze(
    transfers: Sequence[dict[str, Any]],
    freeze_account: str,
    freeze_time: str,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """transfers: [{from, to, amount, timestamp}] (chronological order applied
    internally). Returns preserved amounts and the audit trail of decisions."""
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    if len(transfers) > cfg["max_events"]:
        raise ValueError("transfer set exceeds max_events")
    t_freeze = _ts(freeze_time)

    blocked_at: dict[str, datetime] = {}
    preserved_by_account: dict[str, float] = {}
    balance: dict[str, float] = {}          # counterfactual-world balances
    blocked_out_events: list[dict[str, Any]] = []
    stopped_in_events: list[dict[str, Any]] = []
    unfunded_attempts: list[dict[str, Any]] = []
    completed: list[dict[str, Any]] = []

    for t in sorted(transfers, key=lambda x: _ts(x["timestamp"])):
        ts = _ts(t["timestamp"])
        sender, receiver = str(t["from"]), str(t["to"])
        amount = float(t["amount"])
        rec = {"from": sender, "to": receiver, "amount": amount,
               "timestamp": t["timestamp"]}

        # intervention becomes effective at freeze_time
        if sender == freeze_account and ts >= t_freeze:
            blocked_at.setdefault(sender, ts)
        if receiver == freeze_account and ts >= t_freeze:
            blocked_at.setdefault(receiver, ts)

        sender_frozen = sender in blocked_at and blocked_at[sender] <= ts
        receiver_frozen = receiver in blocked_at and blocked_at[receiver] <= ts

        if sender_frozen:
            # funds stay in the frozen account ONLY if they are actually there
            blocked_out_events.append({
                **rec,
                "reason": ("sender frozen" if balance.get(sender, 0.0) >= amount
                           else "sender frozen (unfunded attempt — funds never "
                                "arrived downstream of the freeze wall)"),
            })
            if balance.get(sender, 0.0) >= amount:
                preserved_by_account[sender] = \
                    preserved_by_account.get(sender, 0.0) + amount
                balance[sender] = balance.get(sender, 0.0) - amount
            else:
                unfunded_attempts.append(rec)
            continue
        if receiver_frozen:
            # money hits the freeze wall and stops there
            preserved_by_account[receiver] = \
                preserved_by_account.get(receiver, 0.0) + amount
            stopped_in_events.append({**rec, "reason": "receiver frozen"})
            continue
        completed.append(rec)
        balance[sender] = balance.get(sender, 0.0) - amount   # negative = external funds
        balance[receiver] = balance.get(receiver, 0.0) + amount

    preserved_total = round(sum(preserved_by_account.values()), 2)
    return {
        "intervention": {"account": freeze_account, "freeze_time": freeze_time},
        "preserved_total": preserved_total,
        "preserved_by_account": {k: round(v, 2) for k, v in preserved_by_account.items()},
        "stopped_in_events": stopped_in_events,
        "blocked_out_events": blocked_out_events,
        "unfunded_attempts": unfunded_attempts,
        "completed_transfers": len(completed),
        "assessment_type": "APPROXIMATED_LOWER_BOUND",
        "epistemic_status": "APPROXIMATED",
        "caveats": [
            "Flows beyond the uploaded statements (cash-out, hawala, off-platform "
            "movement) are unobservable; actual savings could be higher.",
            "This is a model-based estimate for prioritising recovery actions — "
            "NOT admissible proof of negligence or of what a bank would have done.",
            "Blocked-out events assume the freeze would have applied to debits "
            "instantly at the stated time.",
        ],
    }
