# Feature 2 — Contradiction Engine (isolated build)

Finds contradictions no single document states: forged/edited bank figures,
physically impossible movement, and causally impossible event orderings.

## Modules

**A. Ledger audit** (`ledger_audit`) — `balance[i] = balance[i−1] + credit − debit`
per row. Breaks are classified by their *propagation pattern*:
- break **propagates** to subsequent rows → `ALTERED_BALANCE` (a figure was edited
  without fixing the chain),
- break whose successor balances **from the reported value** →
  `MISSING_ROWS_OR_EDITED_BLOCK` (rows removed here, or an edited block) —
  arithmetic alone cannot distinguish these two, and the engine says so,
- **honest limitation:** silently removing a middle row leaves per-row arithmetic
  *clean*; it is caught by `summary_check` (stated totals/closing vs row
  arithmetic) or by Feature 1's version diff.

**B. Impossible travel** (`impossible_travel`) — haversine velocity between an
entity's consecutive geolocated events (CDR tower / ATM / IPDR). Physics is
conservative: `IMPOSSIBLE_TRAVEL` requires the velocity **lower bound** (gap +
clock tolerance) to exceed `impossible_kmh` (default 900) — clock drift cannot
create a false positive. Naive velocity > `suspicious_kmh` (default 200) yields
`SUSPICIOUS_VELOCITY`. Events without coordinates are counted in the output,
never silently dropped. Every finding is `epistemic_status: INFERRED` — tower
and city-level locations never masquerade as GPS.

**C. Temporal ordering** (`temporal_ordering_violations`) — declared causal
rules (`earlier` → `later`, optional `pair_by` field and `max_gap_s`) checked
against timestamps; violations carry both source events.

## Config (defaults, all overridable)

`impossible_kmh: 900, suspicious_kmh: 200, clock_tolerance_s: 600,
min_pair_gap_s: 60, balance_tolerance: 0.01`

## Run tests

```
D:/PROJECTS/cyber_v3/features/.venv/Scripts/python.exe -m pytest tests/ -v
```
13 passed.

## Integration plan (summary)

1. New `contradictions` table (schema in research report) + `GET
   /contradiction/{case_id}/scan`, `GET /contradiction/{case_id}`,
   `PATCH /contradiction/{id}/dismiss` (dismissal requires a reason, is
   audited, and is itself an investigator judgement — never automatic).
2. Ledger rows come from the existing bank parser; travel events need the CDR
   parser's `cell_id` resolved to coordinates — city-level centroid lookup
   first (no TSP tower DB is available; label INFERRED), fine-grained later.
3. Frontend: contradiction cards on the case timeline with computed values
   (distance/velocity/discrepancy) and source citations on every number.
